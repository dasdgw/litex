#
# This file is part of LiteX.
#
# Copyright (c) 2018-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *

from litex.soc.cores.clock.common import *
from litex.soc.cores.clock.intel_common import *

# Intel / CycloneII -------------------------------------------------------------------------------
# values are from cyc2_cii5v1.pdf

class CycloneIIPLL(IntelClocking):
    nclkouts_max   = 3
    n_div_range    = (1, 4+1)
    m_div_range    = (1, 32+1)
    c_div_range    = (1, 512+1) # todo: fill in correct value
    vco_freq_range = (300e6, 1000e6) # todo: If the VCO post-scale counter = 2, then vco_max is 500 MHz
    def __init__(self, speedgrade="-6"):
        self.logger = logging.getLogger("CycloneIIPLL")
        self.logger.info("Creating CycloneIIPLL, {}.".format(colorer("speedgrade {}".format(speedgrade))))
        IntelClocking.__init__(self)
        self.clkin_freq_range = {
            "-6" : (5e6, 420e6),
            "-7" : (5e6, 380e6),
            "-8" : (5e6, 340e6),
        }[speedgrade]
        self.clko_freq_range = {
            "-6" : (0e6, 400e6),
            "-7" : (0e6, 340e6),
            "-8" : (0e6, 280e6),
        }[speedgrade]
