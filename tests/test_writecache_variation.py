import os
import sys
import threading
import time
from snmpsim.commands.responder import main as responder_main
import pytest
from pysnmp.hlapi.asyncio import *
from pysnmp.hlapi.v1arch.asyncio.slim import Slim

import asyncio

TIME_OUT = 10
PORT_NUMBER = 1613


@pytest.fixture(autouse=True)
def setup_args():
    # Store the original sys.argv
    original_argv = sys.argv
    # Define your test arguments here
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data", "writecache")
    test_args = [
        "responder.py",
        f"--data-dir={data_dir}",
        f"--agent-udpv4-endpoint=127.0.0.1:{PORT_NUMBER}",
        f"--debug=app",
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
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysLocation", 0)),
                retries=0,
            )

            assert errorIndication is None
            assert errorStatus == 0
            assert errorIndex == 0
            assert len(varBinds) == 1
            assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysLocation.0"
            assert varBinds[0][1].prettyPrint() == "Unknown"
            assert isinstance(varBinds[0][1], OctetString)

            errorIndication, errorStatus, errorIndex, varBinds = await slim.set(
                "public",
                "localhost",
                PORT_NUMBER,
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysLocation", 0), "Shanghai"),
                retries=0,
            )

            assert errorIndication is None
            assert errorStatus == 0
            assert errorIndex == 0
            assert len(varBinds) == 1
            assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysLocation.0"
            assert varBinds[0][1].prettyPrint() == "Shanghai"
            assert isinstance(varBinds[0][1], OctetString)

            errorIndication, errorStatus, errorIndex, varBinds = await slim.get(
                "public",
                "localhost",
                PORT_NUMBER,
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysLocation", 0)),
                retries=0,
            )

            assert errorIndication is None
            assert errorStatus == 0
            assert errorIndex == 0
            assert len(varBinds) == 1
            assert varBinds[0][0].prettyPrint() == "SNMPv2-MIB::sysLocation.0"
            assert varBinds[0][1].prettyPrint() == "Shanghai"
            assert isinstance(varBinds[0][1], OctetString)
    finally:
        if snmpEngine.transport_dispatcher:
            snmpEngine.transport_dispatcher.close_dispatcher()

        await asyncio.sleep(TIME_OUT)
    # Rest of your test code...
