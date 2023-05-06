#
# This file is part of LiteX.
#
# Copyright (c) 2021 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

# Ultraembedded's USB CDC Device LiteX wrapper:
# USB CDC Core:      https://github.com/ultraembedded/core_usb_cdc
# UMTI <> ULPI Core: https://github.com/ultraembedded/core_ulpi_wrapper

import os

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.interconnect import wishbone
from litex.soc.interconnect import stream

# USB CDC ------------------------------------------------------------------------------------------

class USBCDC(Module):
    def __init__(self, platform, pads):
        self.pads   = pads

        # Control.
        self.enable = Signal(reset=1)

        # Stream Endpoints.
        self.sink   = stream.Endpoint([("data", 8)])
        self.source = stream.Endpoint([("data", 8)])

        # # #

        # Clk/Rst.
        if hasattr(pads, "refclk"):
            self.comb += pads.clk.eq(ClockSignal("usb"))
            self.comb += pads.rst_n.eq(~ResetSignal("usb"))
        else:
            self.clock_domains.cd_usb = ClockDomain()
            self.comb += ClockSignal("usb").eq(pads.clk)
            self.specials += AsyncResetSynchronizer(self.cd_usb, ResetSignal("sys"))

        # UTMI Interface.
        utmi = Record([
            ("data_in",    8),
            ("txready",    1),
            ("rxvalid",    1),
            ("rxactive",   1),
            ("rxerror",    1),
            ("linestate",  2),
            ("data_out",   8),
            ("txvalid",    1),
            ("op_mode",    2),
            ("xcvrselect", 2),
            ("termselect", 1),
            ("dppulldown", 1),
            ("dmpulldown", 1),
        ])

        # Clock Domain Crossing.
        tx_cdc = stream.ClockDomainCrossing([("data", 8)], cd_from="sys", cd_to="usb")
        rx_cdc = stream.ClockDomainCrossing([("data", 8)], cd_from="usb", cd_to="sys")
        self.submodules += tx_cdc, rx_cdc
        self.comb += self.sink.connect(tx_cdc.sink)
        self.comb += rx_cdc.source.connect(self.source)

        # USB CDC Core (UTMI).
        self.specials += Instance("usb_cdc_core",
            # USB Speed.
            p_USB_SPEED_HS = "True",

            # Clk / Rst.
            i_clk_i = ClockSignal("usb"),
            i_rst_i = ResetSignal("usb"),

            # Enable.
            i_enable_i = self.enable,

            # UTMI.
            i_utmi_data_in_i    = utmi.data_in,
            i_utmi_txready_i    = utmi.txready,
            i_utmi_rxvalid_i    = utmi.rxvalid,
            i_utmi_rxactive_i   = utmi.rxactive,
            i_utmi_rxerror_i    = utmi.rxerror,
            i_utmi_linestate_i  = utmi.linestate,
            o_utmi_data_out_o   = utmi.data_out,
            o_utmi_txvalid_o    = utmi.txvalid,
            o_utmi_op_mode_o    = utmi.op_mode,
            o_utmi_xcvrselect_o = utmi.xcvrselect,
            o_utmi_termselect_o = utmi.termselect,
            o_utmi_dppulldown_o = utmi.dppulldown,
            o_utmi_dmpulldown_o = utmi.dmpulldown,

            # Sink.
            i_inport_valid_i   = tx_cdc.source.valid,
            o_inport_accept_o  = tx_cdc.source.ready,
            i_inport_data_i    = tx_cdc.source.data,

            # Source.
            o_outport_valid_o  = rx_cdc.sink.valid,
            i_outport_accept_i = rx_cdc.sink.ready,
            o_outport_data_o   = rx_cdc.sink.data,
        )
        if not os.path.exists("core_usb_cdc"):
            os.system("git clone https://github.com/ultraembedded/core_usb_cdc")
        platform.add_source_dir("core_usb_cdc/src_v", recursive=True)

        # UTMI to ULPI Core.
        pads_data = TSTriple(8)
        self.specials += pads_data.get_tristate(pads.data)
        self.comb += pads_data.oe.eq(~pads.dir)
        self.specials += Instance("ulpi_wrapper",
            # UTMI.
            i_utmi_data_out_i   = utmi.data_out,
            i_utmi_txvalid_i    = utmi.txvalid,
            i_utmi_op_mode_i    = utmi.op_mode,
            i_utmi_xcvrselect_i = utmi.xcvrselect,
            i_utmi_termselect_i = utmi.termselect,
            i_utmi_dppulldown_i = utmi.dppulldown,
            i_utmi_dmpulldown_i = utmi.dmpulldown,
            o_utmi_data_in_o    = utmi.data_in,
            o_utmi_txready_o    = utmi.txready,
            o_utmi_rxvalid_o    = utmi.rxvalid,
            o_utmi_rxactive_o   = utmi.rxactive,
            o_utmi_rxerror_o    = utmi.rxerror,
            o_utmi_linestate_o  = utmi.linestate,

            # ULPI.
            i_ulpi_clk60_i      = ClockSignal("usb"),
            i_ulpi_rst_i        = ResetSignal("usb"),
            i_ulpi_data_out_i   = pads_data.i,
            i_ulpi_dir_i        = pads.dir,
            i_ulpi_nxt_i        = pads.nxt,
            o_ulpi_data_in_o    = pads_data.o,
            o_ulpi_stp_o        = pads.stp,
        )
        if not os.path.exists("core_ulpi_wrapper"):
            os.system("git clone https://github.com/ultraembedded/core_ulpi_wrapper")
        platform.add_source_dir("core_ulpi_wrapper/src_v", recursive=True)
