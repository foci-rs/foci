import status_flags_clear_gate as gate

PRODUCTION_WITH_INLINE_TESTS = """
use foci_tmc4671::registers::STATUS_FLAGS;

#[cfg(test)]
fn helper_before_production() -> u32 {
    STATUS_FLAGS.addr() // not a write
}

pub async fn clear(tmc: &mut T) {
    tmc.write_register(STATUS_FLAGS, 0).await;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writes_status_flags() {
        let ok = matches!(op, SpiOp::Write(addr, 0) if *addr == STATUS_FLAGS.addr());
        backend.write_register(STATUS_FLAGS, 0).await;
    }
}
"""


def test_strip_cfg_test_items_removes_attributed_fns_and_modules():
    stripped = gate.strip_cfg_test_items(PRODUCTION_WITH_INLINE_TESTS)
    assert "helper_before_production" not in stripped
    assert "mod tests" not in stripped
    assert "pub async fn clear" in stripped


def test_find_clear_sites_reports_only_production_writes():
    sites = gate.find_clear_sites(PRODUCTION_WITH_INLINE_TESTS)
    assert sites == [10]


def test_find_clear_sites_matches_raw_address_form():
    source = "9 => write(backend, STATUS_FLAGS.addr(), 0).await,\n"
    assert gate.find_clear_sites(source) == [1]


def test_find_clear_sites_matches_a_call_split_across_lines():
    source = (
        "let _ = backend\n"
        "    .write_register(\n"
        "        STATUS_FLAGS,\n"
        "        0,\n"
        "    )\n"
        "    .await;\n"
    )
    assert gate.find_clear_sites(source) == [3]


def test_main_fails_on_a_writer_outside_the_allowlist(tmp_path):
    src = tmp_path / "shared" / "foci-firmware" / "src" / "tmc_control"
    src.mkdir(parents=True)
    (src / "bootstrap.rs").write_text("retry_plain_write(backend, STATUS_FLAGS, 0)\n")
    (src / "straggler.rs").write_text("tmc.write_register(STATUS_FLAGS, 0).await?;\n")
    assert gate.main(["--workspace-root", str(tmp_path)]) == 1


def test_main_passes_when_only_allowlisted_files_write(tmp_path):
    src = tmp_path / "shared" / "foci-firmware" / "src" / "tmc_control"
    src.mkdir(parents=True)
    (src / "bootstrap.rs").write_text("retry_plain_write(backend, STATUS_FLAGS, 0)\n")
    (src / "interlock.rs").write_text("tmc.write_register(STATUS_FLAGS, 0).await\n")
    assert gate.main(["--workspace-root", str(tmp_path)]) == 0
