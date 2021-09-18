# **************************************************************************
# *
# * Authors:     Carlos Oscar Sorzano (info@kinestat.com)
# *
# * Kinestat Pharma
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'jmdelarosa@cnb.csic.es'
# *
# **************************************************************************

from pyworkflow.tests import *
from pkpd.protocols import *
from pkpd.objects import PKPDDataSet
from .test_workflow import TestWorkflow
import copy

class TestIVIVCWorkflow(TestWorkflow):

    @classmethod
    def setUpClass(cls):
        tests.setupTestProject(cls)

    def testIVIVCWorkflow(self):
        # Check that Simulation is working
        prot = self.newProtocol(ProtPKPDDissolutionSimulate,
                                objLabel='pkpd - simulate dissolution 1st order',
                                modelType=1,
                                parameters="100;0.01",
                                timeUnits=0,
                                resampleT=0.25,
                                resampleTF=800)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the operations ")

if __name__ == "__main__":
    unittest.main()
