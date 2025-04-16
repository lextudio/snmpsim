import os
import sys
import threading
import time
from snmpsim.commands.responder import main as responder_main
import pytest
from pysnmp.hlapi.asyncio import *

import asyncio

TIME_OUT = 5
PORT_NUMBER = 1615  # Using a unique port to avoid conflicts with other tests


@pytest.fixture(autouse=True)
def setup_args():
    # Store the original sys.argv
    original_argv = sys.argv
    # Define your test arguments here
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data", "cisco-nxos")
    test_args = [
        "responder.py",
        f"--data-dir={data_dir}",
        f"--agent-udpv4-endpoint=127.0.0.1:{PORT_NUMBER}",
        # f"--debug=app",
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
    app_thread.join(timeout=1)


@pytest.mark.asyncio
async def test_cisco_cpu_data(run_app_in_background, capsys):
    snmpEngine = SnmpEngine()
    try:
        # Test with SNMPv3 (authPriv)
        authData = UsmUserData(
            "simulator",
            "auctoritas",
            "privatus",
            authProtocol=usmHMACMD5AuthProtocol,
            privProtocol=usmDESPrivProtocol,
        )

        # Use bulkWalkCmd for walking CPU utilization values
        all_results = []

        # Perform bulk walk using bulkWalkCmd
        async for errorIndication, errorStatus, errorIndex, varBinds in bulk_walk_cmd(
            snmpEngine,
            authData,
            await UdpTransportTarget.create(("localhost", PORT_NUMBER), retries=0),
            ContextData(contextName=OctetString("cisco_cpu").asOctets()),
            0,
            25,  # Non-repeaters, Max-repetitions
            ObjectType(
                ObjectIdentity("1.3.6.1.4.1.9.9.91.1.2.1.1")
            ),  # Base OID for CPU stats
            lexicographicMode=False,  # Important: Walk the whole subtree
        ):
            assert errorIndication is None, f"Error: {errorIndication}"
            assert errorStatus == 0, f"Error status: {errorStatus}"
            assert errorIndex == 0, f"Error index: {errorIndex}"

            all_results.extend(varBinds)

        # Verify we got results
        assert len(all_results) > 0, "No CPU data found in bulk walk"

        # The previous additional test with bulkCmd is now redundant as bulkWalkCmd covers it.

    finally:
        if snmpEngine.transport_dispatcher:
            snmpEngine.transport_dispatcher.close_dispatcher()

        await asyncio.sleep(TIME_OUT)
