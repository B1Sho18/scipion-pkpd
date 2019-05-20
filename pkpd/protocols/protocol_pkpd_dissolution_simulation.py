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
# *  e-mail address 'info@kinestat.com'
# *
# **************************************************************************

import numpy as np
import random
from scipy.interpolate import InterpolatedUnivariateSpline

import pyworkflow.protocol.params as params
from pkpd.objects import PKPDExperiment, PKPDSample, PKPDVariable, PKPDFitting
from .protocol_pkpd import ProtPKPD
from pyworkflow.protocol.constants import LEVEL_ADVANCED
from pkpd.models.dissolution_models import *
from pkpd.models.pk_models import *
from pkpd.biopharmaceutics import DrugSource, createDeltaDose, createVia
from pkpd.pkpd_units import createUnit, multiplyUnits, strUnit

# tested in test_workflow_levyplot

class ProtPKPDDissolutionPKSimulation(ProtPKPD):
    """ This protocol simulates the pharmacokinetic response of an ODE model when it is given a single dose of
        an drug whose release is modelled by an in vitro fitting and an in vitro-in vivo correlation."""

    _label = 'simulate PK response'

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):
        form.addSection('Input')
        form.addParam('inputInVitro', params.PointerParam, label="Dissolution profiles in vitro",
                      pointerClass='PKPDFitting', help='Select a fitting with dissolution profiles')
        form.addParam('inputPK', params.PointerParam, label="Pharmacokinetic model",
                      pointerClass='PKPDFitting', help='Select the PK model to be simulated with this input')
        form.addParam('inputIvIvC', params.PointerParam, label="In vitro-In vivo correlation",
                      pointerClass='PKPDExperiment', help='Select the output of an in vitro-in vivo correlation')
        form.addParam('inputDose', params.FloatParam, label="Dose", default=1,
                      help='Make sure that it is in the same units as the ones at which the PK was estimated. '\
                           'This dose will be given simpy once (single dose).')
        form.addParam('inputN', params.IntParam, label="Number of simulations", default=100, expertLevel=LEVEL_ADVANCED)
        form.addParam('t0', params.FloatParam, label="Initial time (h)", default=0)
        form.addParam('tF', params.FloatParam, label="Final time (h)", default=48)
        form.addParam('addIndividuals', params.BooleanParam, label="Add individual simulations", default=False, expertLevel=LEVEL_ADVANCED,
                      help="Individual simulations are added to the output")

    #--------------------------- INSERT steps functions --------------------------------------------
    def _insertAllSteps(self):
        self._insertFunctionStep('simulate',self.inputInVitro.get().getObjId(),self.inputPK.get().getObjId(),
                                 self.inputIvIvC.get().getObjId(),self.inputDose.get(),self.inputN.get())
        self._insertFunctionStep('createOutputStep')

    #--------------------------- STEPS functions --------------------------------------------
    def getInVitroModels(self):
        fnFitting = self.inputInVitro.get().fnFitting
        cls="PKPDSampleFitBootstrap" if fnFitting.get().find("bootstrap")!=-1 else ""
        self.fittingInVitro = PKPDFitting(cls)
        self.fittingInVitro.load(fnFitting)
        self.invitroClsName=self.fittingInVitro.modelDescription.split('(')[1].split(')')[0]

        klass = globals()[self.invitroClsName]
        self.dissolutionModel = klass()
        self.dissolutionPopulation = cls!=""

    def getIVIVProfiles(self):
        experiment = self.readExperiment(self.inputIvIvC.get().fnPKPD,show=False)
        self.allIVIV = []
        for sampleName, sample in experiment.samples.iteritems():
            Fabs=sample.getValues("Fabs")
            Adissol=sample.getValues("Adissol")
            self.allIVIV.append((np.asarray(Adissol,dtype=np.float64),np.asarray(Fabs,dtype=np.float64)))

    def getPKModels(self):
        fnFitting = self.inputPK.get().fnFitting
        cls="PKPDSampleFitBootstrap" if fnFitting.get().find("bootstrap")!=-1 else ""
        self.fittingPK = PKPDFitting(cls)
        self.fittingPK.load(fnFitting)
        modelDescription=self.fittingPK.modelDescription.split(';')[1] # Before ; there is the drug source description
        self.pkClsName=modelDescription.split('(')[1].split(')')[0]

        klass = globals()[self.pkClsName]
        self.pkModel = klass()
        self.pkModel.t0=self.t0.get()*60
        self.pkModel.tF=self.tF.get()*60
        self.pkModel.drugSource = DrugSource()
        dose = createDeltaDose(self.inputDose.get(),via=createVia("Oral; numerical"))
        self.pkModel.drugSource.setDoses([dose], self.t0.get()*60, self.tF.get()*60)
        self.pkPopulation = cls!=""
        self.pkNParams = self.pkModel.getNumberOfParameters()

    def addSample(self, sampleName, t, y):
        newSample = PKPDSample()
        newSample.sampleName = sampleName
        newSample.variableDictPtr = self.outputExperiment.variables
        newSample.doseDictPtr = self.outputExperiment.doses
        newSample.descriptors = {}
        newSample.doseList = ["Bolus"]
        newSample.addMeasurementPattern([self.fittingPK.predicted.varName])
        newSample.addMeasurementColumn("t", t)
        newSample.addMeasurementColumn(self.fittingPK.predicted.varName,y)

        newSample.descriptors["AUC0t"] = self.AUC0t
        newSample.descriptors["AUMC0t"] = self.AUMC0t
        newSample.descriptors["MRT"] = self.MRT
        newSample.descriptors["Cmax"] = self.Cmax
        newSample.descriptors["Tmax"] = self.Tmax
        self.outputExperiment.samples[sampleName] = newSample

    def NCA(self, t, C):
        self.AUC0t = 0
        self.AUMC0t = 0
        t0 = t[0]
        tperiod0=0 # Time at which the dose was given
        for idx in range(0,t.shape[0]-1):
            dt = (t[idx+1]-t[idx])
            if C[idx+1]>=C[idx]: # Trapezoidal in the raise
                self.AUC0t  += 0.5*dt*(C[idx]+C[idx+1])
                self.AUMC0t += 0.5*dt*(C[idx]*t[idx]+C[idx+1]*t[idx+1])
            else: # Log-trapezoidal in the decay
                decrement = C[idx]/C[idx+1]
                K = math.log(decrement)
                B = K/dt
                self.AUC0t  += dt*(C[idx]-C[idx+1])/K
                self.AUMC0t += (C[idx]*(t[idx]-tperiod0)-C[idx+1]*(t[idx+1]-tperiod0))/B-(C[idx+1]-C[idx])/(B*B)

            if idx==0:
                self.Cmax=C[idx]
                self.Tmax=t[idx]-t0
            else:
                if C[idx]>self.Cmax:
                    self.Cmax=C[idx]
                    self.Tmax=t[idx]-t0

        self.MRT = self.AUMC0t/self.AUC0t

        print("   Cmax=%f [%s]"%(self.Cmax,strUnit(self.Cunits.unit)))
        print("   Tmax=%f [min]"%self.Tmax)
        print("   AUC0t=%f [%s]"%(self.AUC0t,strUnit(self.AUCunits)))
        print("   AUMC0t=%f [%s]"%(self.AUMC0t,strUnit(self.AUMCunits)))
        print("   MRT=%f [min]"%self.MRT)

    def simulate(self, objId1, objId2, objId3, inputDose, inputN):
        self.getInVitroModels()
        self.getIVIVProfiles()
        self.getPKModels()

        if self.addIndividuals.get():
            self.outputExperiment = PKPDExperiment()
            tvar = PKPDVariable()
            tvar.varName = "t"
            tvar.varType = PKPDVariable.TYPE_NUMERIC
            tvar.role = PKPDVariable.ROLE_TIME
            tvar.units = createUnit("min")

            self.outputExperiment.variables["t"] = tvar
            self.outputExperiment.variables[self.fittingPK.predicted.varName]=self.fittingPK.predicted
            self.outputExperiment.general["title"]="Simulated ODE response from IVIVC dissolution profiles"
            self.outputExperiment.general["comment"]="Simulated ODE response from IVIVC dissolution profiles"
            for via,_ in self.pkModel.drugSource.vias:
                self.outputExperiment.vias[via.viaName] = via
            for dose in self.pkModel.drugSource.parsedDoseList:
                self.outputExperiment.doses[dose.doseName] = dose

            self.Cunits = self.fittingPK.predicted.units
            self.AUCunits = multiplyUnits(tvar.units.unit, self.Cunits.unit)
            self.AUMCunits = multiplyUnits(tvar.units.unit, self.AUCunits)

            AUCvar = PKPDVariable()
            AUCvar.varName = "AUC0t"
            AUCvar.varType = PKPDVariable.TYPE_NUMERIC
            AUCvar.role = PKPDVariable.ROLE_LABEL
            AUCvar.units = createUnit(strUnit(self.AUCunits))

            AUMCvar = PKPDVariable()
            AUMCvar.varName = "AUMC0t"
            AUMCvar.varType = PKPDVariable.TYPE_NUMERIC
            AUMCvar.role = PKPDVariable.ROLE_LABEL
            AUMCvar.units = createUnit(strUnit(self.AUMCunits))

            MRTvar = PKPDVariable()
            MRTvar.varName = "MRT"
            MRTvar.varType = PKPDVariable.TYPE_NUMERIC
            MRTvar.role = PKPDVariable.ROLE_LABEL
            MRTvar.units = createUnit("min")

            Cmaxvar = PKPDVariable()
            Cmaxvar.varName = "Cmax"
            Cmaxvar.varType = PKPDVariable.TYPE_NUMERIC
            Cmaxvar.role = PKPDVariable.ROLE_LABEL
            Cmaxvar.units = createUnit(strUnit(self.Cunits.unit))

            Tmaxvar = PKPDVariable()
            Tmaxvar.varName = "Tmax"
            Tmaxvar.varType = PKPDVariable.TYPE_NUMERIC
            Tmaxvar.role = PKPDVariable.ROLE_LABEL
            Tmaxvar.units = createUnit("min")

            self.outputExperiment.variables["AUC0t"] = AUCvar
            self.outputExperiment.variables["AUMC0t"] = AUMCvar
            self.outputExperiment.variables["MRT"] = MRTvar
            self.outputExperiment.variables["Cmax"] = Cmaxvar
            self.outputExperiment.variables["Tmax"] = Tmaxvar

        t=np.arange(self.t0.get()*60,self.tF.get()*60,1)
        AUCarray = np.zeros(inputN)
        AUMCarray = np.zeros(inputN)
        MRTarray = np.zeros(inputN)
        CmaxArray = np.zeros(inputN)
        TmaxArray = np.zeros(inputN)
        for i in range(0,inputN):
            print("Simulation no. %d ----------------------"%i)

            # Get a random dissolution profile
            nfit = int(random.uniform(0, len(self.fittingInVitro.sampleFits)))
            sampleFit = self.fittingInVitro.sampleFits[nfit]
            if self.dissolutionPopulation:
                nbootstrap = int(random.uniform(0,sampleFit.parameters.shape[0]))
                dissolutionPrm = sampleFit.parameters[nbootstrap,:]
            else:
                dissolutionPrm = sampleFit.parameters
            print("Dissolution parameters: ",dissolutionPrm)
            A=self.dissolutionModel.forwardModel(dissolutionPrm,t)

            # In vitro-in vivo correlation
            nfit = int(random.uniform(0, len(self.allIVIV)))
            Adissol, Fabs = self.allIVIV[nfit]
            B=InterpolatedUnivariateSpline(Adissol,Fabs,k=1)
            A=np.asarray(B(A)[0],dtype=np.float64)

            # Set the dissolution profile
            self.pkModel.drugSource.getVia().viaProfile.setXYValues(t,A)

            # Get a random PK model
            nfit = int(random.uniform(0, len(self.fittingPK.sampleFits)))
            sampleFit = self.fittingPK.sampleFits[nfit]
            if self.pkPopulation:
                nbootstrap = int(random.uniform(0,sampleFit.parameters.shape[0]))
                pkPrm = sampleFit.parameters[nbootstrap,:]
            else:
                pkPrm = sampleFit.parameters
            pkPrm=pkPrm[-self.pkNParams:] # Get the last Nparams
            print("PK parameters: ",pkPrm)
            C=self.pkModel.forwardModel(pkPrm,[t])[0] # forwardModel returns a list of arrays

            self.NCA(t,C)
            AUCarray[i] = self.AUC0t
            AUMCarray[i] = self.AUMC0t
            MRTarray[i] = self.MRT
            CmaxArray[i] = self.Cmax
            TmaxArray[i] = self.Tmax

            if self.addIndividuals:
                self.addSample("Simulation_%d"%i, t, C)

        # Report NCA statistics
        alpha_2 = (100-95)/2
        limits = np.percentile(AUCarray,[alpha_2,100-alpha_2])
        fhSummary=open(self._getPath("summary.txt"),"w")
        self.doublePrint(fhSummary,"AUC %f%% confidence interval=[%f,%f] [%s] mean=%f"%(95,limits[0],limits[1],strUnit(self.AUCunits),np.mean(AUCarray)))
        limits = np.percentile(AUMCarray,[alpha_2,100-alpha_2])
        self.doublePrint(fhSummary,"AUMC %f%% confidence interval=[%f,%f] [%s] mean=%f"%(95,limits[0],limits[1],strUnit(self.AUMCunits),np.mean(AUMCarray)))
        limits = np.percentile(MRTarray,[alpha_2,100-alpha_2])
        self.doublePrint(fhSummary,"MRT %f%% confidence interval=[%f,%f] [min] mean=%f"%(95,limits[0],limits[1],np.mean(MRTarray)))
        limits = np.percentile(CmaxArray,[alpha_2,100-alpha_2])
        self.doublePrint(fhSummary,"Cmax %f%% confidence interval=[%f,%f] [%s] mean=%f"%(95,limits[0],limits[1],strUnit(self.Cunits.unit),np.mean(CmaxArray)))
        limits = np.percentile(CmaxArray,[alpha_2,100-alpha_2])
        self.doublePrint(fhSummary,"Tmax %f%% confidence interval=[%f,%f] [min] mean=%f"%(95,limits[0],limits[1],np.mean(CmaxArray)))
        fhSummary.close()

        if self.addIndividuals:
            self.outputExperiment.write(self._getPath("experiment.pkpd"))

    def createOutputStep(self):
        if self.addIndividuals:
            self._defineOutputs(outputExperiment=self.outputExperiment)
            self._defineSourceRelation(self.inputInVitro.get(), self.outputExperiment)
            self._defineSourceRelation(self.inputPK.get(), self.outputExperiment)
            self._defineSourceRelation(self.inputIvIvC.get(), self.outputExperiment)

    def _validate(self):
        return []

    def _summary(self):
        retval = []
        retval.append('Dose=%f'%self.inputDose.get())
        retval.append('No. simulations=%d'%self.inputN.get())
        retval.append(' ')
        self.addFileContentToMessage(retval,self._getPath("summary.txt"))
        return retval