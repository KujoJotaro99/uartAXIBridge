import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer, with_timeout
from cocotbext.uart import UartSink, UartSource


CLOCK_PERIOD_NS = 83
UART_BAUD = 3000000
UART_BYTE_TIMEOUT_US = 200

REQ_WRITE = 0x10
REQ_READ = 0x11

RAM_ADDR = 0x00000100
WORD_BYTES = 4

KIND_WRITE = "write"
KIND_READ = "read"


class ModelManager:
    """reference model for expected behavior."""

    def __init__(self):
        self.ram = {}

    def run(self, input_data):
        kind, address, data, length = input_data

        # the dut aligns axi accesses to a 32-bit word
        base_address = address & ~0x3

        # this is the byte lane selected by the original address
        byte_offset = address & 0x3
        word = self.ram.get(base_address, bytearray(WORD_BYTES))
        stop = min(byte_offset + length, WORD_BYTES)

        if kind == KIND_WRITE:
            write_bytes = data.to_bytes(WORD_BYTES, "little")
            word[byte_offset:stop] = write_bytes[:stop - byte_offset]
            self.ram[base_address] = word
            return None

        if kind == KIND_READ:
            read_bytes = word[byte_offset:stop]
            read_data = int.from_bytes(read_bytes, "little")
            return address, read_data

        raise AssertionError(f"Unknown transaction kind {kind}")


class InputManager:
    """owns the stimulus stream."""

    def __init__(self, stream):
        self.data = list(stream)
        self.index = 0

    def done(self):
        return self.index >= len(self.data)

    def drive(self, handshake):
        if self.done():
            handshake.drive(None)
            return

        handshake.drive(self.data[self.index])

    def accept(self):
        item = self.data[self.index]
        self.index += 1
        return item


class ScoreManager:
    """checks observed outputs against expected results."""

    def __init__(self, model):
        self.model = model
        self.index = 0

    def update_expected(self, input_data):
        return self.model.run(input_data)

    def check_output(self, expected, output):
        if expected is None:
            return

        address_exp, data_exp = expected
        address_out, data_out = output

        assert int(address_out) == int(address_exp), \
            f"read address mismatch: got {int(address_out):#010x} expected {int(address_exp):#010x}"
        assert int(data_out) == int(data_exp), \
            f"read data mismatch: got {int(data_out):#010x} expected {int(data_exp):#010x}"

        self.index += 1


class HandshakeManager:
    """drives and samples the dut interface."""

    def __init__(self, dut):
        self.dut = dut
        self.current = None
        self.src = UartSource(dut.rx_serial_i, baud=UART_BAUD, bits=8, stop_bits=1)
        self.snk = UartSink(dut.tx_serial_o, baud=UART_BAUD, bits=8, stop_bits=1)

    def drive(self, data):
        self.current = data

    def input_accepted(self):
        return self.current is not None

    async def apply_current(self):
        kind = self.current[0]

        if kind == KIND_WRITE:
            _, address, data, length = self.current
            await self.uart_write(address, data, length)
            await ClockCycles(self.dut.clk_i, 20)
            return None

        if kind == KIND_READ:
            _, address, _, length = self.current
            data = await self.uart_read(address, length)
            return address, data

        raise AssertionError(f"Unknown transaction kind {kind}")

    async def uart_write(self, address, data, length):
        payload = (data & 0xFFFFFFFF).to_bytes(WORD_BYTES, "little")[:length]
        packet = bytes([REQ_WRITE, length]) + address.to_bytes(4, "big") + payload
        await self.src.write(packet)
        await self.src.wait()

    async def uart_read(self, address, length):
        packet = bytes([REQ_READ, length]) + address.to_bytes(4, "big")
        await self.src.write(packet)
        await self.src.wait()

        received = bytearray()
        for _ in range(length):
            await with_timeout(self.snk.wait(), UART_BYTE_TIMEOUT_US, "us")
            received += await self.snk.read(1)
        return int.from_bytes(received, "little")

    async def idle(self):
        self.current = None
        await ClockCycles(self.dut.clk_i, 2)


class TestManager:
    """coordinates the verification components."""

    def __init__(self, dut, stream):
        self.handshake = HandshakeManager(dut)
        self.input = InputManager(stream)
        self.model = ModelManager()
        self.scoreboard = ScoreManager(self.model)

    async def run(self):
        try:
            while not self.input.done():
                self.input.drive(self.handshake)

                if self.handshake.input_accepted():
                    input_data = self.input.accept()
                    expected = self.scoreboard.update_expected(input_data)
                    output = await self.handshake.apply_current()
                    self.scoreboard.check_output(expected, output)

                await FallingEdge(self.handshake.dut.clk_i)
        finally:
            await self.handshake.idle()


async def clock_test(dut):
    await Timer(100, unit="ns")
    cocotb.start_soon(Clock(dut.clk_i, CLOCK_PERIOD_NS, unit="ns").start())
    await Timer(10, unit="ns")


async def reset_test(dut):
    dut.reset_i.value = 1
    dut.rx_serial_i.value = 1
    dut.buttons_i.value = 0

    await FallingEdge(dut.clk_i)
    await FallingEdge(dut.clk_i)

    dut.reset_i.value = 0
    await FallingEdge(dut.clk_i)


@cocotb.test()
async def test_uart_axi_aligned(dut):
    await clock_test(dut)
    await reset_test(dut)

    stream = [
        (KIND_WRITE, RAM_ADDR + 0x00, 0x12345678, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x04, 0xA5A55A5A, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x08, 0x00000000, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x0C, 0xFFFFFFFF, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x00, None, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x04, None, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x08, None, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x0C, None, WORD_BYTES),
    ]

    manager = TestManager(dut, stream)
    await manager.run()


@cocotb.test()
async def test_uart_axi_partial(dut):
    await clock_test(dut)
    await reset_test(dut)

    stream = [
        (KIND_WRITE, RAM_ADDR + 0x00, 0x11223344, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x04, 0xAABBCCDD, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x00, 0xEE, 1),
        (KIND_READ, RAM_ADDR + 0x00, None, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x04, 0xFACE, 2),
        (KIND_READ, RAM_ADDR + 0x04, None, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x00, None, 1),
        (KIND_READ, RAM_ADDR + 0x04, None, 2),
    ]

    manager = TestManager(dut, stream)
    await manager.run()


@cocotb.test()
async def test_uart_axi_misaligned(dut):
    await clock_test(dut)
    await reset_test(dut)

    stream = [
        (KIND_WRITE, RAM_ADDR, 0x11223344, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x01, 0xEE, 1),
        (KIND_READ, RAM_ADDR, None, WORD_BYTES),
        (KIND_WRITE, RAM_ADDR + 0x02, 0xFACE, 2),
        (KIND_READ, RAM_ADDR, None, WORD_BYTES),
        (KIND_READ, RAM_ADDR + 0x01, None, 1),
        (KIND_READ, RAM_ADDR + 0x02, None, 2),
    ]

    manager = TestManager(dut, stream)
    await manager.run()


@cocotb.test()
async def test_uart_axi_random(dut):
    await clock_test(dut)
    await reset_test(dut)

    stream = []
    for index in range(12):
        base_address = RAM_ADDR + 0x40 + (WORD_BYTES * index)
        byte_offset = random.randint(0, WORD_BYTES - 1)
        length = random.randint(1, WORD_BYTES - byte_offset)
        address = base_address + byte_offset
        seed_data = random.getrandbits(32)
        data = random.getrandbits(8 * length)

        stream.append((KIND_WRITE, base_address, seed_data, WORD_BYTES))
        stream.append((KIND_WRITE, address, data, length))
        stream.append((KIND_READ, base_address, None, WORD_BYTES))
        stream.append((KIND_READ, address, None, length))

    manager = TestManager(dut, stream)
    await manager.run()
