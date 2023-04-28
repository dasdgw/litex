#
# This file is part of LiteX.
#
# Copyright (c) 2019 Michael Betz <michibetz@gmail.com>
# Copyright (c) 2019-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.soc.cores.clock.common import *
from litex.soc.cores.clock.xilinx_common import *

# Xilinx / Spartan3 --------------------------------------------------------------------------------

class S3PLL(XilinxClocking):
    nclkouts_max = 6
    clkin_freq_range = (19e6, 540e6)

    def __init__(self, speedgrade=-1):
        self.logger = logging.getLogger("S3PLL")
        self.logger.info("Creating S3PLL, {}.".format(colorer("speedgrade {}".format(speedgrade))))
        XilinxClocking.__init__(self)
        self.divclk_divide_range = (1, 52 + 1)
        self.vco_freq_range      = {
            -1: (400e6, 1000e6),
            -2: (400e6, 1000e6),
            -3: (400e6, 1080e6),
        }[speedgrade]

#   DCM_SP #(
# .CLKDV_DIVIDE(2.0), // Divide by: ...
# done .CLKFX_DIVIDE(1), // Can be any integer from 1 to 32
# done .CLKFX_MULTIPLY(4), // Can be any integer from 2 to 32
# done .CLKIN_DIVIDE_BY_2("FALSE"), // TRUE/FALSE to enable CLKIN divide by two feature
# done .CLKIN_PERIOD(0.0), // Specify period of input clock
# done .CLKOUT_PHASE_SHIFT("NONE"), // Specify phase shift of NONE, FIXED or VARIABLE
# done .CLK_FEEDBACK("1X"), // Specify clock feedback of NONE, 1X or 2X
# done .DESKEW_ADJUST("SYSTEM_SYNCHRONOUS"), // SOURCE_SYNCHRONOUS, SYSTEM_SYNCHRONOUS or an integer from 0 to 15
# done .DLL_FREQUENCY_MODE("LOW"), // HIGH or LOW frequency mode for DLL
# done .DUTY_CYCLE_CORRECTION("TRUE"), // Duty cycle correction, TRUE or FALSE
# done .PHASE_SHIFT(0), // Amount of fixed phase shift from -255 to 255
# done .STARTUP_WAIT("FALSE") // Delay configuration DONE until DCM LOCK, TRUE/FALSE
# ) DCM_SP_inst (
# .CLK0(CLK0), // 0 degree DCM CLK output
# .CLK180(CLK180), // 180 degree DCM CLK output
# .CLK270(CLK270), // 270 degree DCM CLK output
# .CLK2X(CLK2X), // 2X DCM CLK output
# .CLK2X180(CLK2X180), // 2X, 180 degree DCM CLK out
# .CLK90(CLK90), // 90 degree DCM CLK output
# .CLKDV(CLKDV), // Divided DCM CLK out (CLKDV_DIVIDE)
# .CLKFX(CLKFX), // DCM CLK synthesis out (M/D)
# .CLKFX180(CLKFX180), // 180 degree CLK synthesis out
# .LOCKED(LOCKED), // DCM LOCK status output
# .PSDONE(PSDONE), // Dynamic phase adjust done output
# .STATUS(STATUS), // 8-bit DCM status bits output
# .CLKFB(CLKFB), // DCM clock feedback
# .CLKIN(CLKIN), // Clock input (from IBUFG, BUFG or DCM)
# .PSCLK(PSCLK), // Dynamic phase adjust clock input
# .PSEN(PSEN), // Dynamic phase adjust enable input
# .PSINCDEC(PSINCDEC), // Dynamic phase adjust increment/decrement
# .RST(RST) // DCM asynchronous reset input
# );
def do_finalize(self):
        XilinxClocking.do_finalize(self)
        config = self.compute_config()
        pll_fb = Signal()
        self.params.update(
            # Global.
            p_SIM_DEVICE     = "SPARTAN3",
            #p_BANDWIDTH      = "OPTIMIZED",
            p_CLKIN_DIVIDE_BY_2 = "FALSE",
            p_CLKOUT_PHASE_SHIFT = "NONE",
            p_STARTUP_WAIT = "FALSE",
            p_CLK_FEEDBACK = "1X",
            p_DESKEW_ADJUST = "SYSTEM_SYNCHRONOUS", 
            p_DLL_FREQUENCY_MODE = "LOW",
            p_DUTY_CYCLE_CORRECTION = "TRUE",
            #p_COMPENSATION   = "INTERNAL",
            i_RST            = self.reset,
            o_LOCKED         = self.locked,

            # VCO.
            #p_REF_JITTER     = .01, p_CLK_FEEDBACK="CLKFBOUT",
            p_CLKIN_PERIOD  = 1e9/self.clkin_freq,
            p_CLKFX_MULTIPLY  = config["clkfbout_mult"],
            p_PHASE_SHIFT = 0.,
            p_CLKFX_DIVIDE   = config["divclk_divide"],

            i_CLKINSEL       = 1,
            i_CLKIN         = self.clkin,
            i_CLKFBIN        = pll_fb,
            o_CLKFBOUT       = pll_fb,




        )
        for n, (clk, f, p, m) in sorted(self.clkouts.items()):
            self.params["p_CLKOUT{}_DIVIDE".format(n)]     = config["clkout{}_divide".format(n)]
            self.params["p_CLKOUT{}_PHASE".format(n)]      = float(config["clkout{}_phase".format(n)])
            self.params["p_CLKOUT{}_DUTY_CYCLE".format(n)] = 0.5
            self.params["o_CLKOUT{}".format(n)]            = clk
        self.specials += Instance("DCM_SP", **self.params)


class S3DCM(XilinxClocking):
    """ single output with f_out = f_in * {2 .. 256} / {1 .. 256} """
    nclkouts_max = 1
    clkfbout_mult_frange = (2, 256 + 1)
    clkout_divide_range  = (1, 256 + 1)

    def __init__(self, speedgrade=-1):
        self.logger = logging.getLogger("S3DCM")
        self.logger.info("Creating S3DCM, {}.".format(colorer("speedgrade {}".format(speedgrade))))
        XilinxClocking.__init__(self)
        self.divclk_divide_range = (1, 2) # FIXME
        self.clkin_freq_range = {
            -1: (0.5e6, 200e6),
            -2: (0.5e6, 333e6),
            -3: (0.5e6, 375e6),
        }[speedgrade]

        self.vco_freq_range = {
            -1: (5e6, 1e16),
            -2: (5e6, 1e16),
            -3: (5e6, 1e16),
        }[speedgrade]

    def do_finalize(self):
        XilinxClocking.do_finalize(self)
        config = self.compute_config()
        clk, f, p, m = sorted(self.clkouts.items())[0][1]
        self.params.update(
            p_CLKFX_MULTIPLY  = config["clkfbout_mult"],
            p_CLKFX_DIVIDE    = config["clkout0_divide"] * config["divclk_divide"],
            p_SPREAD_SPECTRUM = "NONE",
            p_CLKIN_PERIOD    = 1e9/self.clkin_freq,
            i_CLKIN           = self.clkin,
            i_RST             = self.reset,
            i_FREEZEDCM       = 0,
            o_CLKFX           = clk,
            o_LOCKED          = self.locked,
        )
        self.specials += Instance("DCM_CLKGEN", **self.params)

    def expose_drp(self):
        self._cmd_data      = CSRStorage(10)
        self._send_cmd_data = CSR()
        self._send_go       = CSR()
        self._status        = CSRStatus(4)

        progdata = Signal()
        progen   = Signal()
        progdone = Signal()
        locked   = Signal()

        self.params.update(
            i_PROGCLK         = ClockSignal(),
            i_PROGDATA        = progdata,
            i_PROGEN          = progen,
            o_PROGDONE        = progdone
        )

        remaining_bits = Signal(max=11)
        transmitting   = Signal()
        self.comb += transmitting.eq(remaining_bits != 0)
        sr = Signal(10)
        self.sync += [
            If(self._send_cmd_data.re,
                remaining_bits.eq(10),
                sr.eq(self._cmd_data.storage)
            ).Elif(transmitting,
                remaining_bits.eq(remaining_bits - 1),
                sr.eq(sr[1:])
            )
        ]
        self.comb += [
            progdata.eq(transmitting & sr[0]),
            progen.eq(transmitting | self._send_go.re)
        ]

        # Enforce gap between commands
        busy_counter = Signal(max=14)
        busy         = Signal()
        self.comb += busy.eq(busy_counter != 0)
        self.sync += If(self._send_cmd_data.re,
                busy_counter.eq(13)
            ).Elif(busy,
                busy_counter.eq(busy_counter - 1)
            )

        self.comb += self._status.status.eq(Cat(busy, progdone, self.locked))

        self.logger.info("Exposing DRP interface.")
