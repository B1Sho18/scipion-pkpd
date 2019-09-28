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

import numpy as np
import os

from pyworkflow.tests import *
from pkpd.protocols import *
from pkpd.objects import PKPDDataSet, PKPDExperiment
from test_workflow import TestWorkflow

def unitResponse(D,V,Ka,Cl,t):
    Ke=Cl/V
    t=np.clip(t,0.0,None)
    C=D/V*Ka/(Ka-Ke)*(np.exp(-Ke*t)-np.exp(-Ka*t))
    return C

class TestLevyPlotWorkflow2(TestWorkflow):

    @classmethod
    def setUpClass(cls):
        tests.setupTestProject(cls)

    def testDissolutionWorkflow(self):
        # Create invivo data
        experimentStr = """
[EXPERIMENT] ===========================
comment = 
title = Dissolution

[VARIABLES] ============================
C ; none ; numeric[%f] ; measurement ; Concentration in solution (%)
t ; min ; numeric[%f] ; time ; Time in minutes since start

[VIAS] ================================

[DOSES] ================================

[GROUPS] ================================
__Profile

[SAMPLES] ================================
Profile; group=__Profile

[MEASUREMENTS] ===========================
Profile ; t; C
0 0 
0.25 1.7 
0.5 8.3 
0.75 13.3 
1 20.0 
2 44.0 
3 61.0 
4 70.7 
6 78.0 
8 79.7 
10 80.7 
12 80.0 
16 81.3 
20 82.0 
24 82.3 
"""
        fnExperiment = "experimentInVitro.pkpd"
        fhExperiment = open(fnExperiment, "w")
        fhExperiment.write(experimentStr)
        fhExperiment.close()

        print "Import Experiment in vitro"
        protImport = self.newProtocol(ProtImportExperiment,
                                      objLabel='pkpd - import experiment in vitro',
                                      inputFile=fnExperiment)
        self.launchProtocol(protImport)
        self.assertIsNotNone(protImport.outputExperiment.fnPKPD, "There was a problem with the import")
        self.validateFiles('protImport', protImport)

        os.remove(fnExperiment)

        # Fit a Weibull dissolution
        print "Fitting Weibull model ..."
        protWeibull = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Weibull',
                                globalSearch=True, modelType=3)
        protWeibull.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(protWeibull)
        self.assertIsNotNone(protWeibull.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(protWeibull.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(protWeibull.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>80 and Vmax<82)
        lambdda = float(experiment.samples['Profile'].descriptors['lambda'])
        self.assertTrue(lambdda>0.28 and lambdda<0.29)
        b = float(experiment.samples['Profile'].descriptors['b'])
        self.assertTrue(b>1.4 and b<1.5)

        fitting = PKPDFitting()
        fitting.load(protWeibull.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.997)

        # Create invivo data
        experimentStr = """
[EXPERIMENT] ===========================
comment = Generated as C(t)=D0/V*Ka/(Ka-Ke)*)(exp(-Ke*t)-exp(-Ka*t))
title = My experiment

[VARIABLES] ============================
Cp ; ug/L ; numeric[%f] ; measurement ; Plasma concentration
t ; min ; numeric[%f] ; time ; 

[VIAS] ================================
Oral; splineXY4;  tlag min; bioavailability=1.000000

[DOSES] ================================
Bolus1; via=Oral; bolus; t=0.000000 h; d=200 ug

[GROUPS] ================================
__Individual1

[SAMPLES] ================================
Individual1; dose=Bolus1; group=__Individual1

[MEASUREMENTS] ===========================
Individual1 ; t; Cp
"""
        t = np.arange(0,1000,10)
        Cp = unitResponse(100,50,0.05,0.2,t-20)+unitResponse(100,50,0.05,0.2,t-120)
        for n in range(t.size):
            experimentStr+="%f %f\n"%(t[n],Cp[n])
        fnExperiment ="experimentInVivo.pkpd"
        fhExperiment = open(fnExperiment,"w")
        fhExperiment.write(experimentStr)
        fhExperiment.close()

        print "Import Experiment in vivo"
        protImportInVivo = self.newProtocol(ProtImportExperiment,
                                      objLabel='pkpd - import experiment in vivo',
                                      inputFile=fnExperiment)
        self.launchProtocol(protImportInVivo)
        self.assertIsNotNone(protImportInVivo.outputExperiment.fnPKPD, "There was a problem with the import")
        self.validateFiles('protImport', protImportInVivo)

        os.remove(fnExperiment)

        # Fit Order 1
        print "Fitting splines4-monocompartment model ..."
        protModelInVivo = self.newProtocol(ProtPKPDMonoCompartment,
                                       objLabel='pkpd - fit monocompartment',
                                       bounds="(15.0, 30.0); (0.0, 400.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.0, 1.0); (0.15, 0.25); (47, 53)"
                                       )
        protModelInVivo.inputExperiment.set(protImportInVivo.outputExperiment)
        self.launchProtocol(protModelInVivo)
        self.assertIsNotNone(protModelInVivo.outputExperiment.fnPKPD, "There was a problem with the PK model")
        self.assertIsNotNone(protModelInVivo.outputFitting.fnFitting, "There was a problem with the PK model")
        self.validateFiles('ProtPKPDMonoCompartment', ProtPKPDMonoCompartment)

        experiment = PKPDExperiment()
        experiment.load(protModelInVivo.outputExperiment.fnPKPD)
        V = float(experiment.samples['Individual1'].descriptors['V'])
        self.assertTrue(V>48 and V<52)
        Cl = float(experiment.samples['Individual1'].descriptors['Cl'])
        self.assertTrue(Cl>0.19 and Cl<0.21)

        fitting = PKPDFitting()
        fitting.load(protModelInVivo.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.998)

        # Deconvolve the in vivo
        print "Deconvolving in vivo ..."
        protDeconv = self.newProtocol(ProtPKPDDeconvolve,
                                       objLabel='pkpd - deconvolution'
                                       )
        protDeconv.inputODE.set(protModelInVivo)
        self.launchProtocol(protDeconv)
        self.assertIsNotNone(protDeconv.outputExperiment.fnPKPD, "There was a problem with the deconvolution")
        self.validateFiles('ProtPKPDDeconvolve', ProtPKPDDeconvolve)

        # Levy plot
        print "Levy plot ..."
        protLevy = self.newProtocol(ProtPKPDDissolutionLevyPlot,
                                      objLabel='pkpd - levy plot'
                                      )
        protLevy.inputInVitro.set(protWeibull)
        protLevy.inputInVivo.set(protDeconv)
        self.launchProtocol(protLevy)
        self.assertIsNotNone(protLevy.outputExperimentTime.fnPKPD, "There was a problem with the Levy plot")
        self.validateFiles('ProtPKPDDissolutionLevyPlot', ProtPKPDDissolutionLevyPlot)

        # IVIVC
        print "In vitro-in vivo correlation ..."
        protIVIVC = self.newProtocol(ProtPKPDDissolutionIVIVC,
                                     timeScale=5,
                                     responseScale=1,
                                     objLabel='pkpd - ivivc'
                                    )
        protIVIVC.inputInVitro.set(protWeibull)
        protIVIVC.inputInVivo.set(protDeconv)
        self.launchProtocol(protIVIVC)
        self.assertIsNotNone(protIVIVC.outputExperimentFabs.fnPKPD, "There was a problem with the IVIVC")
        self.assertIsNotNone(protIVIVC.outputExperimentAdissol.fnPKPD, "There was a problem with the IVIVC")
        self.validateFiles('ProtPKPDDissolutionIVIVC', ProtPKPDDissolutionIVIVC)

        # IVIVC generic
        print "In vitro-in vivo generic ..."
        protIVIVCG = self.newProtocol(ProtPKPDDissolutionIVIVCGeneric,
                                      timeScale='$[k1]*$(t)+$[k2]*np.power($(t),2)+$[k3]*np.power($(t),3)',
                                      timeBounds='k1: [0,1]; k2: [-0.01,0];  k3: [0,1e-3]',
                                      responseScale='$[A]*$(Adissol)+$[B]+$[C]*np.power($(Adissol),2)',
                                      responseBounds='A: [0.1,1]; B: [-50,0]; C: [0,0.05]',
                                      objLabel='pkpd - ivivc generic'
                                     )
        protIVIVCG.inputInVitro.set(protWeibull)
        protIVIVCG.inputInVivo.set(protDeconv)
        self.launchProtocol(protIVIVCG)
        self.assertIsNotNone(protIVIVCG.outputExperimentFabs.fnPKPD, "There was a problem with the IVIVC Generic")
        self.validateFiles('ProtPKPDDissolutionIVIVCG', ProtPKPDDissolutionIVIVCGeneric)


if __name__ == "__main__":
    unittest.main()
