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


import unittest, sys
from pyworkflow.em import *
from pyworkflow.tests import *
from pkpd.protocols import *
from pkpd.objects import PKPDDataSet
from test_workflow import TestWorkflow
import copy


class TestDissolutionWorkflow(TestWorkflow):

    @classmethod
    def setUpClass(cls):
        tests.setupTestProject(cls)
        cls.dataset = PKPDDataSet.getDataSet('Dissolution')
        cls.exptFn = cls.dataset.getFile('experiment')

    def testDissolutionWorkflow(self):
        print "Import Experiment"
        protImport = self.newProtocol(ProtImportExperiment,
                                      objLabel='pkpd - import experiment',
                                      inputFile=self.exptFn)
        self.launchProtocol(protImport)
        self.assertIsNotNone(protImport.outputExperiment.fnPKPD, "There was a problem with the import")
        self.validateFiles('protImport', protImport)

        # Fit a zero order dissolution
        print "Fitting 0th order ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                 objLabel='pkpd - fit dissolution 0th order',
                                 globalSearch=True,modelType=0)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        K = float(experiment.samples['Profile'].descriptors['K'])
        self.assertTrue(K>5.20 and K<5.22)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.38)

        print "Fitting 0th order tlag ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution 0th order tlag',
                                globalSearch=True, modelType=0, allowTlag=True)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        K = float(experiment.samples['Profile'].descriptors['K'])
        tlag = float(experiment.samples['Profile'].descriptors['tlag'])
        self.assertTrue(K > 5.20 and K < 5.22)
        self.assertTrue(tlag>=0.0 and tlag < 0.001)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2 > 0.38)

        # Fit a first order dissolution
        print "Fitting 1st order ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                 objLabel='pkpd - fit dissolution 1st order',
                                 globalSearch=True,modelType=1)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>83 and Vmax<83.5)
        beta = float(experiment.samples['Profile'].descriptors['beta'])
        self.assertTrue(beta>0.37 and beta<0.38)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.985)


        # Fit a fractional order dissolution
        print "Fitting fractional order ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution fractional order',
                                globalSearch=True, modelType=2)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>80 and Vmax<81)
        beta = float(experiment.samples['Profile'].descriptors['beta'])
        self.assertTrue(beta>7.35 and beta<7.45)
        alpha = float(experiment.samples['Profile'].descriptors['alpha'])
        self.assertTrue(alpha>0.74 and alpha<0.76)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.995)


        # Fit a Weibull dissolution
        print "Fitting Weibull model ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Weibull',
                                globalSearch=True, modelType=3)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>80 and Vmax<82)
        lambdda = float(experiment.samples['Profile'].descriptors['lambda'])
        self.assertTrue(lambdda>0.28 and lambdda<0.29)
        b = float(experiment.samples['Profile'].descriptors['b'])
        self.assertTrue(b>1.4 and b<1.5)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.997)
        protWeibull = copy.copy(prot)


        # Fit a Higuchi dissolution
        print "Fitting Higuchi model ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Higuchi',
                                globalSearch=True, modelType=4)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>22 and Vmax<22.5)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.78)


        # Fit a Korsmeyer-Peppas dissolution
        print "Fitting Korsmeyer-Peppas model ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Korsmeyer-Peppas',
                                globalSearch=True, modelType=5)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>32 and Vmax<32.5)
        m = float(experiment.samples['Profile'].descriptors['m'])
        self.assertTrue(m>0.3 and m<0.4)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.84)


        # Fit a Hixson-Crowell dissolution
        print "Fitting Hixson-Crowell model ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Hixson-Crowell',
                                globalSearch=True, modelType=6)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>80 and Vmax<86.5)
        K = float(experiment.samples['Profile'].descriptors['K'])
        self.assertTrue(K>0.06 and K<0.12)

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.90)


        # Fit a Hopfenberg dissolution
        print "Fitting Hopfenberg order ..."
        prot = self.newProtocol(ProtPKPDDissolutionFit,
                                objLabel='pkpd - fit dissolution Hopfenberg',
                                globalSearch=True, modelType=7)
        prot.inputExperiment.set(protImport.outputExperiment)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputExperiment.fnPKPD, "There was a problem with the dissolution model ")
        self.assertIsNotNone(prot.outputFitting.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDDissolutionFit', ProtPKPDDissolutionFit)
        experiment = PKPDExperiment()
        experiment.load(prot.outputExperiment.fnPKPD)
        Vmax = float(experiment.samples['Profile'].descriptors['Vmax'])
        self.assertTrue(Vmax>80 and Vmax<83)
        K = float(experiment.samples['Profile'].descriptors['K'])
        self.assertTrue((K>0.040 and K<0.045) or (K>0.15 and K<0.25))
        m = float(experiment.samples['Profile'].descriptors['m'])
        self.assertTrue((m>1 and m<2) or (m>8 and m<9))

        fitting = PKPDFitting()
        fitting.load(prot.outputFitting.fnFitting)
        self.assertTrue(fitting.sampleFits[0].R2>0.985)


        # Check that fit bootstrap is working
        print "Fitting bootstrap ..."
        prot = self.newProtocol(ProtPKPDFitBootstrap,
                                objLabel='pkpd - fit bootstrap')
        prot.inputFit.set(protWeibull)
        self.launchProtocol(prot)
        self.assertIsNotNone(prot.outputPopulation.fnFitting, "There was a problem with the dissolution model ")
        self.validateFiles('ProtPKPDFitBootstrap', ProtPKPDFitBootstrap)

        fitting = PKPDFitting("PKPDSampleFitBootstrap")
        fitting.load(prot.outputPopulation.fnFitting)
        mu, sigma, R, percentiles = fitting.getStats()
        self.assertTrue(mu[0]>80.5 and mu[0]<81.5)
        self.assertTrue(mu[1]>0.28 and mu[1]<0.29)
        self.assertTrue(mu[2]>1.4 and mu[2]<1.5)

if __name__ == "__main__":
    unittest.main()
