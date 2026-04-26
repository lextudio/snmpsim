import sys


def test_cmd2rec_send_varbinds_compat(monkeypatch, tmp_path):
    # Simulate newer pysnmp which exposes snake_case API only
    from pysnmp.entity.rfc3413 import cmdgen as pysnmp_cmdgen

    class StubNextCommandGenerator:
        def __init__(self, *args, **kwargs):
            pass

        def send_varbinds(self, *args, **kwargs):
            # noop implementation using snake_case name only
            return None

    # Patch the NextCommandGenerator (and Bulk) used by snmpsim.commands.cmd2rec
    monkeypatch.setattr(pysnmp_cmdgen, "NextCommandGenerator", StubNextCommandGenerator)
    monkeypatch.setattr(pysnmp_cmdgen, "BulkCommandGenerator", StubNextCommandGenerator)

    # Stub SnmpEngine to avoid starting a real transport dispatcher
    from pysnmp.entity import engine as pysnmp_engine, config as pysnmp_config

    class StubTransportDispatcher:
        def runDispatcher(self):
            return

        def closeDispatcher(self):
            return

    class StubSnmpEngine:
        def __init__(self):
            self.transportDispatcher = StubTransportDispatcher()

        def getMibBuilder(self):
            return None

    monkeypatch.setattr(pysnmp_engine, "SnmpEngine", StubSnmpEngine)

    # Make pysnmp config helpers no-ops so they don't touch engine internals
    monkeypatch.setattr(pysnmp_config, "addV1System", lambda *a, **k: None)
    monkeypatch.setattr(pysnmp_config, "addTargetParams", lambda *a, **k: None)
    monkeypatch.setattr(pysnmp_config, "addSocketTransport", lambda *a, **k: None)
    monkeypatch.setattr(pysnmp_config, "addTargetAddr", lambda *a, **k: None)
    monkeypatch.setattr(pysnmp_config, "addV3User", lambda *a, **k: None)

    # Provide minimal CLI args: agent endpoint and output file
    args = [
        "snmpsim-record-commands",
        "--agent-udpv4-endpoint",
        "127.0.0.1:161",
        "--output-file",
        str(tmp_path / "out.snmprec"),
    ]
    monkeypatch.setattr(sys, "argv", args)

    import snmpsim.commands.cmd2rec as cmd2rec

    # Running main() should not raise AttributeError and should exit cleanly
    rc = cmd2rec.main()
    assert rc == 0
