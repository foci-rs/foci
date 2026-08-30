import pytest
import rtic_future_gate

TYPE_SIZES = """\
print-type-size type: `{async fn body of app::tmc_control()}`: 13240 bytes, \
alignment: 8 bytes
print-type-size     field `.await_ty`: 13000 bytes
print-type-size type: `rtic::export::executor::AsyncTaskExecutor<{async fn \
body of app::tmc_control()}>`: 13248 bytes, alignment: 8 bytes
print-type-size type: `core::pin::Pin<&mut {async fn body of \
app::tmc_control()}>`: 4 bytes, alignment: 4 bytes
print-type-size type: `{async fn body of app::identify()}`: 512 bytes, \
alignment: 4 bytes
"""

SIZE_OUTPUT = """\
   text\t   data\t    bss\t    dec\t    hex\tfilename
 123456\t    100\t  29628\t 153184\t  25660\topenffboard-fw
"""

MEMORY_X = """\
MEMORY
{
  FLASH : ORIGIN = 0x08008000, LENGTH = 992K
  RAM   : ORIGIN = 0x20000000, LENGTH = 128K
}
"""

MEMORY_X_WITH_ATTRS = """\
MEMORY
{
  FLASH (rx) : ORIGIN = 0x08008000, LENGTH = 1008K
  RAM (rwx)  : ORIGIN = 0x20000000, LENGTH = 128K
}
"""


def test_parse_size_literal_handles_kilobytes():
    assert rtic_future_gate.parse_size_literal("128K") == 128 * 1024


def test_parse_size_literal_handles_hex():
    assert rtic_future_gate.parse_size_literal("0x20000") == 0x20000


def test_parse_size_literal_handles_bare_bytes():
    assert rtic_future_gate.parse_size_literal("512") == 512


def test_parse_size_literal_rejects_garbage():
    with pytest.raises(ValueError):
        rtic_future_gate.parse_size_literal("not-a-size")


def test_parse_memory_x_region_bytes_finds_named_region_without_attrs():
    assert rtic_future_gate.parse_memory_x_region_bytes(MEMORY_X, "RAM") == 128 * 1024


def test_parse_memory_x_region_bytes_finds_named_region_with_attrs():
    assert rtic_future_gate.parse_memory_x_region_bytes(MEMORY_X_WITH_ATTRS, "RAM") == 128 * 1024


def test_parse_memory_x_region_bytes_raises_when_missing():
    with pytest.raises(ValueError):
        rtic_future_gate.parse_memory_x_region_bytes(MEMORY_X, "CCMRAM")


def test_parse_future_bytes_matches_the_bare_future_type():
    size = rtic_future_gate.parse_future_bytes(TYPE_SIZES, "app::tmc_control")
    assert size == 13240


def test_parse_future_bytes_ignores_larger_wrapper_types():
    # AsyncTaskExecutor<{async fn body of app::tmc_control()}> is 13248 bytes
    # -- 8 bytes larger than the bare future -- and must not be picked.
    size = rtic_future_gate.parse_future_bytes(TYPE_SIZES, "app::tmc_control")
    assert size != 13248


def test_parse_future_bytes_raises_when_task_absent():
    with pytest.raises(ValueError):
        rtic_future_gate.parse_future_bytes(TYPE_SIZES, "app::no_such_task")


def test_parse_size_output_extracts_data_and_bss():
    data, bss = rtic_future_gate.parse_size_output(SIZE_OUTPUT)
    assert (data, bss) == (100, 29628)


def test_parse_size_output_raises_on_missing_row():
    with pytest.raises(ValueError):
        rtic_future_gate.parse_size_output("text data bss dec hex filename\n")


def test_free_ram_bytes_subtracts_static_allocation():
    assert rtic_future_gate.free_ram_bytes(128 * 1024, 100, 29628) == 131072 - 100 - 29628


def test_check_variant_reports_no_failures_within_budget(tmp_path):
    type_sizes_path = tmp_path / "type-sizes.txt"
    type_sizes_path.write_text(TYPE_SIZES)
    memory_x_path = tmp_path / "memory.x"
    memory_x_path.write_text(MEMORY_X)
    elf_path = tmp_path / "openffboard-fw"
    elf_path.write_bytes(b"\x7fELF")

    variant = rtic_future_gate.BoardVariant(
        board="openffboard-fw",
        variant="release",
        task_path="app::tmc_control",
        memory_x_region="RAM",
        future_max_bytes=16_384,
        free_ram_min_bytes=60 * 1024,
        type_sizes_path=type_sizes_path,
        elf_path=elf_path,
        memory_x_path=memory_x_path,
    )

    original_run_size = rtic_future_gate.run_size
    rtic_future_gate.run_size = lambda _elf: SIZE_OUTPUT
    try:
        failures = rtic_future_gate.check_variant(variant)
    finally:
        rtic_future_gate.run_size = original_run_size

    assert failures == []


def test_check_variant_flags_future_size_over_budget(tmp_path):
    type_sizes_path = tmp_path / "type-sizes.txt"
    type_sizes_path.write_text(TYPE_SIZES)
    memory_x_path = tmp_path / "memory.x"
    memory_x_path.write_text(MEMORY_X)
    elf_path = tmp_path / "openffboard-fw"
    elf_path.write_bytes(b"\x7fELF")

    variant = rtic_future_gate.BoardVariant(
        board="openffboard-fw",
        variant="release",
        task_path="app::tmc_control",
        memory_x_region="RAM",
        future_max_bytes=1_000,
        free_ram_min_bytes=60 * 1024,
        type_sizes_path=type_sizes_path,
        elf_path=elf_path,
        memory_x_path=memory_x_path,
    )

    original_run_size = rtic_future_gate.run_size
    rtic_future_gate.run_size = lambda _elf: SIZE_OUTPUT
    try:
        failures = rtic_future_gate.check_variant(variant)
    finally:
        rtic_future_gate.run_size = original_run_size

    assert len(failures) == 1
    assert "exceeds 1000-byte budget" in failures[0]


def test_check_variant_flags_free_ram_below_floor(tmp_path):
    type_sizes_path = tmp_path / "type-sizes.txt"
    type_sizes_path.write_text(TYPE_SIZES)
    memory_x_path = tmp_path / "memory.x"
    memory_x_path.write_text(MEMORY_X)
    elf_path = tmp_path / "openffboard-fw"
    elf_path.write_bytes(b"\x7fELF")

    variant = rtic_future_gate.BoardVariant(
        board="openffboard-fw",
        variant="release",
        task_path="app::tmc_control",
        memory_x_region="RAM",
        future_max_bytes=16_384,
        free_ram_min_bytes=200 * 1024,
        type_sizes_path=type_sizes_path,
        elf_path=elf_path,
        memory_x_path=memory_x_path,
    )

    original_run_size = rtic_future_gate.run_size
    rtic_future_gate.run_size = lambda _elf: SIZE_OUTPUT
    try:
        failures = rtic_future_gate.check_variant(variant)
    finally:
        rtic_future_gate.run_size = original_run_size

    assert len(failures) == 1
    assert "below 204800-byte floor" in failures[0]


def test_default_variants_covers_both_boards_and_variants(tmp_path):
    variants = rtic_future_gate.default_variants(tmp_path)
    labels = {(v.board, v.variant) for v in variants}
    assert labels == {
        ("openffboard-fw", "release"),
        ("openffboard-fw", "trace"),
        ("ouroboros-fw", "release"),
        ("ouroboros-fw", "trace"),
    }


def test_default_variants_use_the_shared_bare_task_path(tmp_path):
    variants = rtic_future_gate.default_variants(tmp_path)
    assert all(v.task_path == "app::tmc_control" for v in variants)
