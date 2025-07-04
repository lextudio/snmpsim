import os
import sys
import threading
import time
from snmpsim.commands.responder import main as responder_main
import pytest
from pysnmp.hlapi.asyncio import *
from pysnmp.hlapi.v1arch.asyncio.slim import Slim

import asyncio

TIME_OUT = 5
PORT_NUMBER = 1612


@pytest.fixture(autouse=True)
def setup_args():
    # Store the original sys.argv
    original_argv = sys.argv
    # Define your test arguments here
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data", "UPS")
    test_args = [
        "responder.py",
        f"--data-dir={data_dir}",
        f"--agent-udpv4-endpoint=127.0.0.1:{PORT_NUMBER}",
        f"--debug=all",
        f"--timeout={TIME_OUT}",
    ]
    # Set sys.argv to your test arguments
    sys.argv = test_args
    # This will run before the test function
    yield
    # Restore the original sys.argv after the test function has finished
    sys.argv = original_argv


# Fixture to run the application in a separate thread
@pytest.fixture
def run_app_in_background():
    def target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            responder_main()
        except KeyboardInterrupt:
            print("Application interrupted.")
        finally:
            print("Application stopped.")
            loop.close()

    app_thread = threading.Thread(target=target)
    app_thread.start()
    # Allow some time for the application to initialize and run
    time.sleep(1)
    yield
    # Simulate KeyboardInterrupt after the test is done
    # This part may need to be adjusted based on how your application handles shutdown
    app_thread.join(timeout=1)


@pytest.mark.asyncio
async def test_main_with_specific_args(run_app_in_background, capsys):
    snmpEngine = SnmpEngine()
    try:
        # Create SNMP GET request v1
        with Slim(1) as slim:
            errorIndication, errorStatus, errorIndex, varBinds = await slim.get(
                "public",
                "localhost",
                PORT_NUMBER,
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
                retries=0,
            )

            assert errorIndication is None
            assert errorStatus == 0
            assert errorIndex == 0
            assert len(varBinds) == 1
            assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysDescr.0"
            assert (
                varBinds[0][1].prettyPrint()
                == "APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.7.2 PN:apc_hw05_aos_672.bin AF1:v6.7.2 AN1:apc_hw05_rpdu2g_672.bin MN:AP8932 HR:02 SN: 3F503A169043 MD:01/23/2019)"
            )
            assert isinstance(varBinds[0][1], OctetString)

        # # v2c
        with Slim() as slim:
            errorIndication, errorStatus, errorIndex, varBinds = await slim.get(
                "public",
                "localhost",
                PORT_NUMBER,
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
                retries=0,
            )

            assert errorIndication is None
            assert errorStatus == 0
            assert errorIndex == 0
            assert len(varBinds) == 1
            assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysDescr.0"
            assert (
                varBinds[0][1].prettyPrint()
                == "APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.7.2 PN:apc_hw05_aos_672.bin AF1:v6.7.2 AN1:apc_hw05_rpdu2g_672.bin MN:AP8932 HR:02 SN: 3F503A169043 MD:01/23/2019)"
            )
            assert isinstance(varBinds[0][1], OctetString)

        # v3
        authData = UsmUserData(
            "simulator",
            "auctoritas",
            "privatus",
            authProtocol=usmHMACMD5AuthProtocol,
            privProtocol=usmDESPrivProtocol,
        )
        transport = await UdpTransportTarget.create(("localhost", PORT_NUMBER), retries=0)
        errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
            snmpEngine,
            authData,
            transport,
            ContextData(contextName=OctetString("public").asOctets()),
            ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
            retries=0,
        )

        assert errorIndication is None
        assert errorStatus == 0
        assert len(varBinds) == 1
        assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysDescr.0"
        assert (
            varBinds[0][1].prettyPrint()
            == "APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.7.2 PN:apc_hw05_aos_672.bin AF1:v6.7.2 AN1:apc_hw05_rpdu2g_672.bin MN:AP8932 HR:02 SN: 3F503A169043 MD:01/23/2019)"
        )
        assert isinstance(varBinds[0][1], OctetString)

    finally:
        if snmpEngine.transport_dispatcher:
            snmpEngine.transport_dispatcher.close_dispatcher()

        await asyncio.sleep(TIME_OUT)
    # Rest of your test code...
