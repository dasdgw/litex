#
# This file is part of LiteX.
#
# Copyright (c) 2021 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2023 Michael Frank <michifrank2@gmx.de>
# SPDX-License-Identifier: BSD-2-Clause

# Ultraembedded's USB HOST Device LiteX wrapper:
# USB HOST Core:     https://github.com/ultraembedded/core_usb_host
# UMTI <> ULPI Core: https://github.com/ultraembedded/core_ulpi_wrapper

import pprint

import os

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.soc.interconnect import wishbone
from litex.soc.interconnect import axi
from litex.soc.interconnect import stream
from litex.soc.interconnect.csr import *

# USB HOST ------------------------------------------------------------------------------------------

class UsbHost(Module, AutoCSR):
    def __init__(self, platform, s_axil, pads):
        self.pads   = pads

        # Control.
        #self.enable = Signal(reset=1)

        # Stream Endpoints.
        #self.sink   = stream.Endpoint([("data", 8)])
        #self.source = stream.Endpoint([("data", 8)])

        # # #

        #Clk/Rst.
        if hasattr(pads, "refclk"):
            self.comb += pads.clk.eq(ClockSignal("usb"))
            self.comb += pads.rst_n.eq(~ResetSignal("usb"))
        else:
            self.clock_domains.cd_usb = ClockDomain()
            self.comb += ClockSignal("usb").eq(pads.clk)
            self.specials += AsyncResetSynchronizer(self.cd_usb, ResetSignal("sys"))

        self.dummy_clk = Signal()
        self.comb += self.dummy_clk.eq(ClockSignal("usb"))
        self.count_usb = Signal(8)
        self.sync += self.count_usb.eq(self.count_usb + 1)

        # AXI-Lite.
        #if bus_standard == "axi-lite":
        #self.axil_bus = axil_bus = axi.AXILiteInterface(address_width=32, data_width=32)
        #platform.add_extension(axil_bus.get_ios("bus"))
        #self.comb += axil_bus.connect_to_pads(platform.request("bus"), mode="slave")
        #self.bus.add_slave("usbh_host", slave=axil_bus, region=SoCRegion(origin=0x50000000, size=0x000000100))

        #pprint.pprint(axil_bus.__dict__)

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
        #tx_host = stream.ClockDomainCrossing([("data", 8)], cd_from="sys", cd_to="usb")
        #rx_host = stream.ClockDomainCrossing([("data", 8)], cd_from="usb", cd_to="sys")
        #self.submodules += tx_host, rx_host
        #self.comb += self.sink.connect(tx_host.sink)
        #self.comb += rx_host.source.connect(self.source)


        self.intr_o = Signal()
        # Interrupt Interface ----------------------------------------------------------------------
        #self.comb += self.platform.request("interrupt").eq(self.ethmac.ev.irq)

        # USB HOST Core (UTMI).
        self.specials += Instance("usbh_host",
            # USB Speed.
            #p_USB_SPEED_HS = "True",
            p_USB_CLK_FREQ = "60e6",
            #p_USB_CLK_FREQ = "48e6",

            # Clk / Rst.
            i_clk_i = ClockSignal("usb"),
            i_rst_i = ResetSignal("usb"),

            # Enable.
            #i_enable_i = self.enable,

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

            # axi-lite in
            i_cfg_awvalid_i = s_axil.aw.valid,
            i_cfg_awaddr_i  = s_axil.aw.addr,
            i_cfg_wvalid_i  = s_axil.w.valid,
            i_cfg_wdata_i   = s_axil.w.data,
            i_cfg_wstrb_i   = s_axil.w.strb,
            i_cfg_bready_i  = s_axil.b.ready,
            i_cfg_arvalid_i = s_axil.ar.valid,
            i_cfg_araddr_i  = s_axil.ar.addr,
            i_cfg_rready_i  = s_axil.r.ready,

            # axi-lite out
            o_cfg_awready_o = s_axil.aw.ready,
            o_cfg_wready_o  = s_axil.w.ready,
            o_cfg_bvalid_o  = s_axil.b.valid,
            o_cfg_bresp_o   = s_axil.b.resp,
            o_cfg_arready_o = s_axil.ar.ready,
            o_cfg_rvalid_o  = s_axil.r.valid,
            o_cfg_rdata_o   = s_axil.r.data,
            o_cfg_rresp_o   = s_axil.r.resp,

            # irq
            o_intr_o=self.intr_o,
        )
        if not os.path.exists("core_usb_host"):
            os.system("git clone https://github.com/ultraembedded/core_usb_host")
        print("******************************************************************************************* bufu")
        platform.add_source_dir("core_usb_host/src_v", recursive=True)
        import inspect
        print(os.path.abspath(inspect.getfile(platform.add_source_dir)))
        #print("abort in usb_host")
        #os.abort()

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
        # todo remove next line
        self.comb += pads.reset.eq(0)
        if not os.path.exists("core_ulpi_wrapper"):
            os.system("git clone https://github.com/ultraembedded/core_ulpi_wrapper")
        platform.add_source_dir("core_ulpi_wrapper/src_v", recursive=True)
