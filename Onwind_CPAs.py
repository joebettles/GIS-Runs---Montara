"""
CPA Model exported as python.
Name : CPAs - Onshore Wind
Group : External Runs
With QGIS : 31613
"""

# This script creates CPAs with relevant attributes from an input raster. 
# The script links to files in the shared Dropbox folder - " GIS Runs - Montara"
# There are only two steps required to run the file:
    # 1. Set the filepath to point to the Dropbox folder on your computer. Here it is set up on my MacOS
    # 2. When you run the script you will be prompted to enter the resource raster, choose the raster that corresponds to 
        # a. the technology type and,
        # b. the exclusion scenario
# Finally, when running you have the ability to save the file to your desired location.
# Select 'CSV' when pointing to the output location for the attribute table of the resulting CPAs




##### SET FILEPATH #######
######  VVVVVVV  #########
#filepath = "/Users/elesl/Dropbox/GIS Runs - Montara/Run_files/"
filepath = "/Users/joebettles/Dropbox/GIS Runs - Montara/Run_files/"
#####   ^^^^^^^  ########



from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterBoolean
import processing

class CpasOnwind(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        # This is the length of bounding box for the CPAs.
        self.addParameter(QgsProcessingParameterNumber('CPAGridLength', 'CPA Grid Length', type=QgsProcessingParameterNumber.Integer, minValue=500, maxValue=5000, defaultValue=1400))
        # This is a Lambert Azimuthal Equal Area Projection used as the standard for European Commission spatial publications.
        self.addParameter(QgsProcessingParameterCrs('EuropeCRS', 'Europe CRS', defaultValue='EPSG:3035'))
        # Select Input Resource Raster from Files
        self.addParameter(QgsProcessingParameterRasterLayer('ResourceRaster', 'Resource Raster', defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Cpas', 'CPAs', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterBoolean('VERBOSE_LOG', 'Verbose logging', optional=True, defaultValue=False))


    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(32, model_feedback)
        results = {}
        outputs = {}

        # Repr Substations
        alg_params = {
            'INPUT': filepath+'5_transmissionAndInfrastructure/ENTSO_Substations/entso_substations.shp',
            'OPERATION': '',
            'TARGET_CRS': parameters['EuropeCRS'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ReprSubstations'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Fix Substations
        alg_params = {
            'INPUT': outputs['ReprSubstations']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixSubstations'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Fixed Boundary Layer
        alg_params = {
            'INPUT': filepath+'3_geographicBoundaries/NUTS_2_Boundries/NUTS_RG_10M_2021_3857_LEVL_2.shp',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixedBoundaryLayer'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Reclassify by table
        alg_params = {
            'DATA_TYPE': 1,
            'INPUT_RASTER': parameters['ResourceRaster'],
            'NODATA_FOR_MISSING': False,
            'NO_DATA': -9999,
            'RANGE_BOUNDARIES': 0,
            'RASTER_BAND': 1,
            'TABLE': [0,100,1],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ReclassifyByTable'] = processing.run('native:reclassifybytable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # CF Grid
        alg_params = {
            'CRS': 'ProjectCrs',
            'EXTENT': outputs['FixedBoundaryLayer']['OUTPUT'],
            'HOVERLAY': 0,
            'HSPACING': parameters['CPAGridLength'],
            'TYPE': 1,
            'VOVERLAY': 0,
            'VSPACING': parameters['CPAGridLength'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CfGrid'] = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Fix Grid
        alg_params = {
            'INPUT': outputs['CfGrid']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixGrid'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Polygonize (raster to vector)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['ReclassifyByTable']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonizeRasterToVector'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Add x field
        alg_params = {
            'FIELD_LENGTH': 1,
            'FIELD_NAME': 'x',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,
            'FORMULA': '1',
            'INPUT': outputs['PolygonizeRasterToVector']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddXField'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Fix polys
        alg_params = {
            'INPUT': outputs['AddXField']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixPolys'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Dissolve
        alg_params = {
            'FIELD': ['x'],
            'INPUT': outputs['FixPolys']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Dissolve'] = processing.run('native:dissolve', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Fix Resource Polys
        alg_params = {
            'INPUT': outputs['Dissolve']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixResourcePolys'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Grided Resource
        # Create CPA grid by splitting the resource polygons with the grid lines.
        alg_params = {
            'INPUT': outputs['FixResourcePolys']['OUTPUT'],
            'LINES': outputs['FixGrid']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GridedResource'] = processing.run('native:splitwithlines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Resource with CF
        # Assign a sample mean of the underlying CF raster to the created polygons.
        alg_params = {
            'COLUMN_PREFIX': 'CF_',
            'INPUT': outputs['GridedResource']['OUTPUT'],
            'INPUT_RASTER': parameters['ResourceRaster'],
            'RASTER_BAND': 1,
            'STATISTICS': [2],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ResourceWithCf'] = processing.run('native:zonalstatisticsfb', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Corrected CF
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'CF',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,
            'FORMULA': '\"CF_mean\" * 0.85',
            'INPUT': outputs['ResourceWithCf']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CorrectedCf'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Fix CF Polys
        alg_params = {
            'INPUT': outputs['CorrectedCf']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixCfPolys'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Calc: resource area polygon
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'SqKm',
            'FIELD_PRECISION': 7,
            'FIELD_TYPE': 0,
            'FORMULA': '$area/1000000',
            'INPUT': outputs['FixCfPolys']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcResourceAreaPolygon'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # Remove CPAs below cutoff
        alg_params = {
            'FIELD': 'SqKm',
            'INPUT': outputs['CalcResourceAreaPolygon']['OUTPUT'],
            'OPERATOR': 2,
            'VALUE': '0.5',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RemoveCpasBelowCutoff'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Calc: Nameplate Capacity
        alg_params = {
            'FIELD_LENGTH': 15,
            'FIELD_NAME': 'Name_cap',
            'FIELD_PRECISION': 6,
            'FIELD_TYPE': 0,
            'FORMULA': '\"SqKm\" * 5',
            'INPUT': outputs['RemoveCpasBelowCutoff']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcNameplateCapacity'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Total GW
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'Name_cap_gw',
            'FIELD_PRECISION': 5,
            'FIELD_TYPE': 0,
            'FORMULA': '\"Name_cap\"/1000',
            'INPUT': outputs['CalcNameplateCapacity']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['TotalGw'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # Calc: Annual Generation
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'An_gen',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '\"Name_cap\" * 8760 *\"CF\"',
            'INPUT': outputs['TotalGw']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcAnnualGeneration'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Calc: Plant Capital Cost
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'Plant_cost',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '\"Name_cap\" * 1480024',
            'INPUT': outputs['CalcAnnualGeneration']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcPlantCapitalCost'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Distance to substations
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'FIELDS_TO_COPY': ['Sub_ID'],
            'INPUT': outputs['CalcPlantCapitalCost']['OUTPUT'],
            'INPUT_2': outputs['FixSubstations']['OUTPUT'],
            'MAX_DISTANCE': None,
            'NEIGHBORS': 1,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DistanceToSubstations'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # Calc: Interconnection Cost
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'Inter_cost',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '517056 * (\"distance\"/1000)',
            'INPUT': outputs['DistanceToSubstations']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcInterconnectionCost'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # Calc: Total Capital Cost
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'Total_cost',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '\"Plant_cost\" + \"Inter_cost\"',
            'INPUT': outputs['CalcInterconnectionCost']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcTotalCapitalCost'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # Calc: Annual Payments
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'An_payments',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '\"Total_cost\" * 0.073',
            'INPUT': outputs['CalcTotalCapitalCost']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcAnnualPayments'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # Calc: LCOE
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'LCOE',
            'FIELD_PRECISION': 3,
            'FIELD_TYPE': 0,
            'FORMULA': '\"An_payments\" / \"An_gen\"',
            'INPUT': outputs['CalcAnnualPayments']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcLcoe'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # NUTS IDs to CPAs
        alg_params = {
            'INPUT': outputs['CalcLcoe']['OUTPUT'],
            'INPUT_FIELDS': [''],
            'OVERLAY': outputs['FixedBoundaryLayer']['OUTPUT'],
            'OVERLAY_FIELDS': ['NUTS_ID'],
            'OVERLAY_FIELDS_PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['NutsIdsToCpas'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Create Substatiuon NUTS_ID
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Sub_NUTS_ID',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': 'substr(\"Sub_ID\",5,4)',
            'INPUT': outputs['NutsIdsToCpas']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CreateSubstatiuonNuts_id'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(28)
        if feedback.isCanceled():
            return {}

        # COUNTRY IDs to CPAs
        alg_params = {
            'INPUT': outputs['CreateSubstatiuonNuts_id']['OUTPUT'],
            'INPUT_FIELDS': [''],
            'OVERLAY': filepath+'3_geographicBoundaries/NUTS_2_Boundries/NUTS_RG_10M_2021_3857_LEVL_2.shp',
            'OVERLAY_FIELDS': ['CNTR_CODE'],
            'OVERLAY_FIELDS_PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CountryIdsToCpas'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(29)
        if feedback.isCanceled():
            return {}

        # Calc: CPA_ID
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'CPA_ID',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': '@row_number',
            'INPUT': outputs['CountryIdsToCpas']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalcCpa_id'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(30)
        if feedback.isCanceled():
            return {}

        # Unique ID
        alg_params = {
            'FIELD_LENGTH': 20,
            'FIELD_NAME': 'E37_CPA_ID',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,
            'FORMULA': 'concat(\"NUTS_ID\",\'_\',\"CPA_ID\")',
            'INPUT': outputs['CalcCpa_id']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['UniqueId'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(31)
        if feedback.isCanceled():
            return {}

        # Drop field(s)
        alg_params = {
            'COLUMN': ['fid','DN','x','n','feature_x','feature_y','nearest_x','nearest_y'],
            'INPUT': outputs['UniqueId']['OUTPUT'],
            'OUTPUT': parameters['Cpas']
        }
        outputs['DropFields'] = processing.run('qgis:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Cpas'] = outputs['DropFields']['OUTPUT']
        return results

    def name(self):
        return 'CPAs - Onwind'

    def displayName(self):
        return 'CPAs - Onwind'

    def group(self):
        return 'External Runs'

    def groupId(self):
        return 'External Runs'

    def createInstance(self):
        return CpasOnwind()
