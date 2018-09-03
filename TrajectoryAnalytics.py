from itertools import groupby
from operator import itemgetter
import numpy as np
import pandas as pd
from operator import mul
import itertools
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report
from haversine import haversine
from datetime import datetime
import math
import matplotlib.pyplot as plt
from Utils import *
from Classifiers import *
from Evaluation import *
from scipy.stats import ttest_ind, ttest_ind_from_stats
from Plotter import *

class TrajectoryAnalytics:
    def __init__(self, fileName):
        self.dataList = self.preProcessing(fileName)
        print("Step 1 successful")
        self.dataAll = self.calculatePointFeatures()
        print("Step 2 successful")
        self.dataAllMeasures = self.calculateSubTrajectories()
        print("Step 3 successful")
        self.similarTransportationModes()  # This is just for plotting the data
        print("Step 4 successful")
        self.dataSubTrajectories = pd.DataFrame(self.dataAllMeasures, columns= Utils.columns)
        self.dataSubTrajectories = self.dataSubTrajectories.drop(['t_user_id', 'date_Start', 'flag'], axis=1)
        self.classify()
        print("Step 5 successful")
        self.evaluteResults()
        print("Step 6 successful")


    def preProcessing(self, fileName):
        '''
        First we read the csv file. Loading the Input Data and sorting it in ascending order
        of 't_user_id' and 'collected_time'. This way of sorting the data is equivalent to
        grouping the data on the bases of 't_user_id' and 'collected_time'.
        Param :- self
        Return :- dataList
        '''
        df = pd.read_csv(fileName)
        total = len(df)
        df = df.sort_values(['t_user_id', 'collected_time'], ascending=True).reset_index(drop=True)
        x = df['collected_time'].str.split(' ', expand=True)
        df['date_Start'] = x[0]
        y = x[1].str.split('-', expand=True)
        df['time_Start'] = y[0]
        df['latitude_Start'] = df['latitude']
        df['longitude_Start'] = df['longitude']
        df['latitude_End'] = df['latitude'].drop([0]).reset_index(drop=True)
        df['longitude_End'] = df['longitude'].drop([0]).reset_index(drop=True)
        df['date_End'] = df['date_Start'].drop([0]).reset_index(drop=True)
        df['time_End'] = df['time_Start'].drop([0]).reset_index(drop=True)
        df['UserChk'] = df['t_user_id'].drop([0]).reset_index(drop=True)
        df['ModeChk'] = df['transportation_mode'].drop([0]).reset_index(drop=True)
        df = df.drop('collected_time', axis=1)
        df = df.drop('latitude', axis=1)
        df = df.drop('longitude', axis=1)
        df = df.drop([total - 1], axis=0)
        '''
        Columns of processable data now are :- 
        't_user_id', 'transportation_mode', 'date_Start', 'time_Start',
        ' latitude_Start', 'longitude_Start', 'latitude_End', 'longitude_End',
        'date_End', 'time_End', 'UserChk', 'ModeChk' 
        We finally convert this DataFrame to list of lists because of the better time complexity of lists than pandas DataFrame
        '''
        return df.values.tolist()

    def calculatePointFeatures(self):
        '''
        Here we are calculating distance, speed, acceleration and bearing.

        Filtering the data so as to remove as per our preprocessed data and understanding of trajectories.
        We are filtering:-
        1. The information if starting inf is from 1 user and ending inf is from another user
        2. The information if starting inf is from 1 transportation mode and ending inf is from another transportation mode
        3. If the starting date and ending date match or not
        '''

        FMT = '%H:%M:%S'
        filteredData = [item for item in self.dataList
                        if item[0] == item[10] and item[1] == item[11] and item[2] == item[8]]

        # Here we are creating a flag numerical column so as to easily find when there is a change in subtrajectory or trajectory
        startId = filteredData[0][0]
        startMode = filteredData[0][1]
        startDate = filteredData[0][2]
        subTrajGrper = []
        count = 1
        for row in filteredData:
            if (startId == row[0] and startMode == row[1] and startDate == row[2]):
                subTrajGrper.append(count)
            else:
                startId = row[0]
                startMode = row[1]
                startDate = row[2]
                count += 1
                subTrajGrper.append(count)
        # Calculating Distance
        distance = [haversine((float(row[4]), float(row[5])), (float(row[6]), float(row[7]))) * 1000.0 for row in
                    filteredData]
        # Calculating Time
        time = [(datetime.strptime(str(row[9]), FMT) - datetime.strptime(str(row[3]), FMT)).seconds for row in
                filteredData]
        # Calculating speed
        speed = [x / y if y != 0 else 0 for x, y in zip(distance, time)]
        # Calculating acceleration
        pairedSpeed = list(Utils.pairwise(speed))
        acceleration = [(x[1] - x[0]) / y if (y != 0 and x[1] != None) else 0 for x, y in zip(pairedSpeed, time)]
        # Calculating Bearing
        bearing = [Utils.bearing_Calculator(row) for row in filteredData]

        # Here we are doing a list compression so as to add the answer of Q1 to our preprocessed data.
        dataA1Soln = [u + [v, w, x, y, z] for u, v, w, x, y, z in
                      zip(filteredData, subTrajGrper, distance, speed, acceleration, bearing)]

        # Here we are masking the accleration to 0 in case it is calculated by change in speed between 2 different users.
        pairedA1 = list(Utils.pairwise(dataA1Soln))
        self.dataA1Soln = [list(map(mul, rows[0], [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1])) if (
                    rows[1] != None and rows[0][12] != rows[1][12]) else rows[0] for rows in pairedA1]
        return dataA1Soln

    def calculateSubTrajectories(self):
        ##### Creating sub trajectories #####

        # We are filtering the data to contain only the useful columns for calculating A2 and A3
        list1 = [0, 1, 2, 12, 13, 14, 15, 16]
        dataImp = [[each_list[i] for i in list1] for each_list in self.dataA1Soln]

        # Grouping the data for A2
        dataSubTrajectory = [list(items) for _, items in groupby(dataImp, itemgetter(0, 1, 2, 3))]

        # Filtering the subtrajectories which have points less than 10
        dataFiltSubTrj = [grp for grp in dataSubTrajectory if (len(grp) > 10)]

        # Calculating all the statistical values for A2. Here we calculate the
        # minimum, maximum, mean and median for every subtrajectory.
        A2Traj = []
        count = 0
        for grp in dataFiltSubTrj:
            count += 1
            statsDistance = Utils.stats_Calculator([distanceRow[4] for distanceRow in grp])
            statsSpeed = Utils.stats_Calculator([speedRow[5] for speedRow in grp])
            statsAcceleration = Utils.stats_Calculator([accRow[6] for accRow in grp])
            statsBearing = Utils.stats_Calculator([bearRow[7] for bearRow in grp])

            x1 = [grp[0][0], grp[0][1], grp[0][2], grp[0][3]]
            A2Traj.append(x1 + statsDistance + statsSpeed + statsAcceleration + statsBearing)

        # Filtering the subrajectories of motorcycle and run
        A2FiltTraj = [trj for trj in A2Traj if (trj[1] != 'motorcycle' and trj[1] != 'run')]

        return A2FiltTraj

        # TODO: Fix this stuff
        '''
        # Convert the filtered data into pandas DataFrame as it has a very optimized groupby function
        omes = ('Bus', 'Car ', 'Subway', 'Taxi', 'Train', 'Walk')
        arrRfH = [np.mean(cvRfHierarchyT[0]), np.mean(cvRfHierarchyT[1]), np.mean(cvRfHierarchyT[2]),
                  np.mean(cvRfHierarchyT[3]), np.mean(cvRfHierarchyT[4]), np.mean(cvRfHierarchyT[5])]
        arrRfF = [np.mean(cvRfFlatT[0]), np.mean(cvRfFlatT[1]), np.mean(cvRfFlatT[2]), np.mean(cvRfFlatT[3]),
                  np.mean(cvRfFlatT[4]), np.mean(cvRfFlatT[5])]

        N = 6

        locx = np.arange(6)  # the x locations for the groups
        width = 0.15  # the width of the bars

        fig, ax = plt.subplots()
        rects1 = ax.bar(locx, arrRfH, width, color='r')
        rects2 = ax.bar(locx + width, arrRfF, width, color='y')

        ax.set_ylabel('Accuracy Values')
        ax.set_title('Class wise RF comparison among Hierarchy and Flat')
        ax.set_xticks(locx + width / 2)
        ax.set_xticklabels(model_names)
        ax.set_yticks(np.arange(0, 1.04, 0.05))
        ax.legend((rects1[0], rects2[0]), ('Hierarchy Structure', 'Flat Structure'))

        plt.show()
        '''


    def similarTransportationModes(self):
        # Filtering the data so as to keep only those columns which will be useful
        # for analysing the feature values by class.
        list2 = [0, 1, 2, 3, 6, 11, 16, 21]
        A2FiltTrajF = [[each_list2[i] for i in list2] for each_list2 in self.dataAllMeasures]

        output = pd.DataFrame(A2FiltTrajF, columns=['t_user_id', 'transportation_mode', 'date_Start', 'Flag'
            , 'meanDis', 'meanSpeed', 'meanAcc', 'meanBrng'])

        # Grouping by the mode so as to analyse the silimarities and disimilarities between classes
        outgrp = output.groupby(['transportation_mode'])

        # Computing the mean per class for the 4 feature values i.e distance, speed, acceleration and bearing.
        dicPerType = {}
        for grpType in outgrp:
            label = grpType[0]
            grp = grpType[1]
            data = []
            data.append(np.mean(grp['meanDis']))
            data.append(np.mean(grp['meanSpeed']))
            data.append(np.mean(grp['meanAcc']))
            data.append(np.mean(grp['meanBrng']))
            dicPerType[label] = data

        # Plotting analysis using bar plot
        count = 0
        features = [0, 1, 2, 3]
        keys = ['mean distance', 'mean speed', 'mean acceleration', 'mean bearing']
        xLabels = ['bus', 'car', 'subway', 'taxi', 'train', 'walk']
        Plotter.plotSimilarities(dicPerType, keys, xLabels)

    def classify(self):
        modelDic = {}
        trainData = self.dataSubTrajectories.iloc[0:4708, 1:21]
        trainLabels = self.dataSubTrajectories.iloc[0:4708, 0]
        testData = self.dataSubTrajectories.iloc[4708:5885, 1:21]
        testLabels = self.dataSubTrajectories.iloc[4708:5885, 0]

        result = Classifiers.fitHierarchyRFC(trainData, trainLabels, modelDic)
        predLabels = Evaluation.predictHierarchy(testData, result)
        target_names = ['train', 'subway', 'walk', 'car', 'taxi', 'bus']
        print("CLASSIFICATION REPORT :- ")
        print(classification_report(testLabels, predLabels, target_names=target_names))
        print("ACCURACY OF COMPLETE HIERARCHY :- ")
        print(accuracy_score(testLabels, predLabels))

        rfc = RandomForestClassifier()
        rfc.fit(trainData, trainLabels)
        predFlatRFC = rfc.predict(testData)
        target_names = ['train', 'subway', 'walk', 'car', 'taxi', 'bus']
        print("CLASSIFICATION REPORT :- ")
        print(classification_report(testLabels, predFlatRFC, target_names=target_names))
        print("ACCURACY OF COMPLETE FLAT STRUCTURE :- ")
        print(accuracy_score(testLabels, predFlatRFC))

        result = Classifiers.fitHierarchyDTC(trainData, trainLabels, modelDic)
        predLabels = Evaluation.predictHierarchy(testData, result)
        target_names = ['train', 'subway', 'walk', 'car', 'taxi', 'bus']
        print("CLASSIFICATION REPORT :- ")
        print(classification_report(testLabels, predLabels, target_names=target_names))
        print("ACCURACY OF COMPLETE HIERARCHY :- ")
        print(accuracy_score(testLabels, predLabels))

        dtc = DecisionTreeClassifier()
        dtc.fit(trainData, trainLabels)
        predFlatDTC = dtc.predict(testData)
        target_names = ['train', 'subway', 'walk', 'car', 'taxi', 'bus']
        print("CLASSIFICATION REPORT :- ")
        print(classification_report(testLabels, predFlatDTC, target_names=target_names))
        print("ACCURACY OF COMPLETE FLAT STRUCTURE :- ")
        print(accuracy_score(testLabels, predFlatDTC))

    def evaluteResults(self):
        trainData = self.dataSubTrajectories.iloc[:, 1:21]
        trainLabels = self.dataSubTrajectories.iloc[:, 0]

        cvRfHierarchy = Evaluation.cvStratified(trainData, trainLabels, 'RandomForestHierarchy')
        cvDtHierarchy = Evaluation.cvStratified(trainData, trainLabels, 'DecisionTreeHierarchy')
        cvRfFlat = Evaluation.cvStratified(trainData, trainLabels, 'RandomForestFlat')
        cvDtFlat = Evaluation.cvStratified(trainData, trainLabels, 'DecisionTreeFlat')

        cvRfHierarchyT = Utils.transformer(cvRfHierarchy[0])
        cvDtHierarchyT = Utils.transformer(cvDtHierarchy[0])
        cvRfFlatT = Utils.transformer(cvRfFlat[0])
        cvDtFlatT = Utils.transformer(cvDtFlat[0])


        t_1, p_1 = ttest_ind(cvRfHierarchy[1], cvRfFlat[1], equal_var=False)
        print('Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_1))
        if p_1 > 0.05:
            print('=> Samples are likely drawn from the same distributions ')
        else:
            print('=> Samples are likely drawn from different distributions ')
        print()

        t_2, p_2 = ttest_ind(cvDtHierarchy[1], cvDtFlat[1], equal_var=False)
        print('Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_2))
        if p_2 > 0.05:
            print('=> Samples are likely drawn from the same distributions ')
        else:
            print('=> Samples are likely drawn from different distributions ')
        print()


        t_1, p_1 = ttest_ind(cvRfHierarchyT[0], cvRfFlatT[0], equal_var=False)
        print(
            'Bus Class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_1))
        if p_1 > 0.05:
            print('=> Bus samples are likely drawn from the same distributions ')
        else:
            print('=> Bus samples are likely drawn from different distributions ')
        print()

        t_2, p_2 = ttest_ind(cvRfHierarchyT[1], cvRfFlatT[1], equal_var=False)
        print(
            'Car Class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_2))
        if p_2 > 0.05:
            print('=> Car samples are likely drawn from the same distributions ')
        else:
            print('=> Car samples are likely drawn from different distributions ')
        print()

        t_3, p_3 = ttest_ind(cvRfHierarchyT[2], cvRfFlatT[2], equal_var=False)
        print(
            'Subway Class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_3))
        if p_3 > 0.05:
            print('=> Subway samples are likely drawn from the same distributions ')
        else:
            print('=> Subway samples are likely drawn from different distributions ')
        print()

        t_4, p_4 = ttest_ind(cvRfHierarchyT[3], cvRfFlatT[3], equal_var=False)
        print(
            'Taxi class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_4))
        if p_4 > 0.05:
            print('=> Taxi samples are likely drawn from the same distributions ')
        else:
            print('=> Taxi samples are likely drawn from different distributions ')
        print()

        t_5, p_5 = ttest_ind(cvRfHierarchyT[4], cvRfFlatT[4], equal_var=False)
        print(
            'Train class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_5))
        if p_5 > 0.05:
            print('=> Train samples are likely drawn from the same distributions ')
        else:
            print('=> Train samples are likely drawn from different distributions ')
        print()

        t_6, p_6 = ttest_ind(cvRfHierarchyT[5], cvRfFlatT[5], equal_var=False)
        print(
            'Walk class Comparing Random Forest classifier on hierarchical structure with Random Forest on a Flat Structure')
        print('p value from t test for this is {}'.format(p_6))
        if p_6 > 0.05:
            print('=> Walk samples are likely drawn from the same distributions ')
        else:
            print('=> Walk samples are likely drawn from different distributions ')
        print()

        t_7, p_7 = ttest_ind(cvDtHierarchyT[0], cvDtFlatT[0], equal_var=False)
        print(
            'Bus class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_7))
        if p_7 > 0.05:
            print('=> Bus samples are likely drawn from the same distributions ')
        else:
            print('=> Bus samples are likely drawn from different distributions ')
        print()

        t_8, p_8 = ttest_ind(cvDtHierarchyT[1], cvDtFlatT[1], equal_var=False)
        print(
            'Car class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_8))
        if p_8 > 0.05:
            print('=> Car samples are likely drawn from the same distributions ')
        else:
            print('=> Car samples are likely drawn from different distributions ')
        print()

        t_9, p_9 = ttest_ind(cvDtHierarchyT[2], cvDtFlatT[2], equal_var=False)
        print(
            'Subway class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_9))
        if p_9 > 0.05:
            print('=> Subway samples are likely drawn from the same distributions ')
        else:
            print('=> Subway samples are likely drawn from different distributions ')
        print()

        t_10, p_10 = ttest_ind(cvDtHierarchyT[3], cvDtFlatT[3], equal_var=False)
        print(
            'Taxi class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_10))
        if p_10 > 0.05:
            print('=> Taxi samples are likely drawn from the same distributions ')
        else:
            print('=> Taxi samples are likely drawn from different distributions ')
        print()

        t_11, p_11 = ttest_ind(cvDtHierarchyT[4], cvDtFlatT[4], equal_var=False)
        print(
            'Train class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_11))
        if p_11 > 0.05:
            print('=> Train samples are likely drawn from the same distributions ')
        else:
            print('=> Train samples are likely drawn from different distributions ')
        print()

        t_12, p_12 = ttest_ind(cvDtHierarchyT[5], cvDtFlatT[5], equal_var=False)
        print(
            'Walk class Comparing Decision Tree classifier on hierarchical structure with Decision Tree on a Flat Structure')
        print('p value from t test for this is {}'.format(p_12))
        if p_12 > 0.05:
            print('=> Walk samples are likely drawn from the same distributions ')
        else:
            print('=> Walk samples are likely drawn from different distributions ')
        print()

if __name__ == '__main__':
    obj = TrajectoryAnalytics("geolife_raw.csv")