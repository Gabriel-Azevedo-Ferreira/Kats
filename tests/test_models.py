#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest
from unittest import TestCase

import numpy as np
import pandas as pd
from infrastrategy.kats.consts import TimeSeriesData
from infrastrategy.kats.models.ar_net import ARNet
from infrastrategy.kats.models.arima import ARIMAModel, ARIMAParams
from infrastrategy.kats.models.harmonic_regression import (
    HarmonicRegressionModel,
    HarmonicRegressionParams,
)
from infrastrategy.kats.models.holtwinters import HoltWintersModel, HoltWintersParams
from infrastrategy.kats.models.linear_model import LinearModel, LinearModelParams
from infrastrategy.kats.models.lstm import LSTMModel, LSTMParams
from infrastrategy.kats.models.prophet import ProphetModel, ProphetParams
from infrastrategy.kats.models.quadratic_model import (
    QuadraticModel,
    QuadraticModelParams,
)
from infrastrategy.kats.models.sarima import SARIMAModel, SARIMAParams
from infrastrategy.kats.models.stlf import STLFModel, STLFParams
from infrastrategy.kats.models.theta import ThetaModel, ThetaParams
from infrastrategy.kats.models.var import VARModel, VARParams
from infrastrategy.kats.models.bayesian_var import BayesianVAR, BayesianVARParams
from infrastrategy.kats.parameter_tuning.time_series_parameter_tuning import (
    TimeSeriesParameterTuning,
)
from infrastrategy.kats.utils.emp_confidence_int import EmpConfidenceInt
from infrastrategy.kats.models.nowcasting.feature_extraction import LAG, MOM, MA, ROC, MACD

DATA = pd.read_csv("infrastrategy/kats/data/air_passengers.csv")
DATA.columns = ["time", "y"]
TSData = TimeSeriesData(DATA)

DATA_daily = pd.read_csv("infrastrategy/kats/data/peyton_manning.csv")
DATA_daily.columns = ["time", "y"]
TSData_daily = TimeSeriesData(DATA_daily)

DATA_multi = pd.read_csv("infrastrategy/kats/data/multi_ts.csv")
TSData_multi = TimeSeriesData(DATA_multi)

ALL_ERRORS = ["mape", "smape", "mae", "mase", "mse", "rmse"]


class DataValidationTest(TestCase):
    def test_data_validation(self):
        # add the extra data point to break the frequency.
        extra_point = pd.DataFrame(
            [["1900-01-01", 2], ["2020-01-01", 2]], columns=["time", "y"]
        )
        data_with_extra_point = DATA.copy().append(extra_point)

        tsData_with_missing_point = TimeSeriesData(data_with_extra_point)

        tsData_with_missing_point.validate_data(
            validate_frequency=False, validate_dimension=False
        )
        tsData_with_missing_point.validate_data(
            validate_frequency=False, validate_dimension=True
        )
        with self.assertRaises(ValueError, msg="Frequency validation should fail."):
            tsData_with_missing_point.validate_data(
                validate_frequency=True, validate_dimension=False
            )
        with self.assertRaises(ValueError, msg="Frequency validation should fail."):
            tsData_with_missing_point.validate_data(
                validate_frequency=True, validate_dimension=True
            )


class ARIMAModelTest(TestCase):
    def test_fit_forecast(self):
        params = ARIMAParams(p=1, d=1, q=1)
        m = ARIMAModel(data=TSData, params=params)
        m.fit(
            start_params=None,
            transparams=True,
            method="css-mle",
            trend="c",
            solver="lbfgs",
            maxiter=500,
            full_output=1,
            disp=False,
            callback=None,
            start_ar_lags=None,
        )
        m.predict(steps=30)
        m.plot()

        m_daily = ARIMAModel(data=TSData_daily, params=params)
        m_daily.fit()
        m_daily.predict(steps=30)
        m.plot()

    def test_others(self):
        params = ARIMAParams(p=1, d=1, q=1)
        params.validate_params()
        m = ARIMAModel(data=TSData, params=params)

        # test __str__ method
        self.assertEqual(m.__str__(), "ARIMA")

        # test input error
        self.assertRaises(
            ValueError,
            ARIMAModel,
            TSData_multi,
            params,
        )

        # test search space
        self.assertEqual(m.get_parameter_search_space(),
            [
            {
                "name": "p",
                "type": "choice",
                "values": list(range(1, 6)),
                "value_type": "int",
                "is_ordered": True,
            },
            {
                "name": "d",
                "type": "choice",
                "values": list(range(1, 3)),
                "value_type": "int",
                "is_ordered": True,
            },
            {
                "name": "q",
                "type": "choice",
                "values": list(range(1, 6)),
                "value_type": "int",
                "is_ordered": True,
            },
        ]
        )


class ThetaModelTest(TestCase):
    def test_fit_forecast(self):
        params = ThetaParams(m=12)
        m = ThetaModel(TSData, params)
        m.fit()
        m.predict(steps=15, alpha=0.05)
        m.plot()

        params = ThetaParams()
        m_daily = ThetaModel(data=TSData_daily, params=params)
        m_daily.fit()
        m_daily.predict(steps=30)
        m.plot()

        params = ThetaParams(m=12)
        m = ThetaModel(TSData, params)
        m.fit()
        m.predict(steps=15, alpha=0.05, include_history=True)
        m.plot()

        params = ThetaParams()
        m_daily = ThetaModel(data=TSData_daily, params=params)
        m_daily.fit()
        m_daily.predict(steps=30, include_history=True)
        m.plot()

    def test_others(self):
        params = ThetaParams(m=12)
        params.validate_params()

        self.assertRaises(
            ValueError,
            ThetaModel,
            TSData_multi,
            params,
        )

        m = ThetaModel(TSData, params)

        # test __str__ method
        self.assertEqual(m.__str__(), "Theta")


class HoltWintersModelTest(TestCase):
    def test_fit_forecast(self):
        params = HoltWintersParams(
            trend=None,
            damped=False,
            seasonal=None,
            seasonal_periods=None,
        )
        m = HoltWintersModel(data=TSData, params=params)
        m.fit()
        m.predict(steps=30)
        m.plot()

        m_daily = HoltWintersModel(data=TSData_daily, params=params)
        m_daily.fit()
        m_daily.predict(steps=30)
        m.plot()

    def test_others(self):
        # test param validation
        self.assertRaises(
            ValueError,
            HoltWintersParams,
            trend="random_trend",
        )

        self.assertRaises(
            ValueError,
            HoltWintersParams,
            seasonal="random_seasonal",
        )

        params = HoltWintersParams()
        self.assertRaises(
            ValueError,
            HoltWintersModel,
            TSData_multi,
            params,
        )

        m = HoltWintersModel(TSData, params)

        # test __str__ method
        self.assertEqual(m.__str__(), "HoltWinters")

        self.assertEqual(m.get_parameter_search_space(),
            [
            {
                "name": "trend",
                "type": "choice",
                "value_type": "str",
                "values": ["additive", "multiplicative"],
            },
            {
                "name": "damped",
                "type": "choice",
                "value_type": "bool",
                "values": [True, False],
            },
            {
                "name": "seasonal",
                "type": "choice",
                "value_type": "str",
                "values": ["additive", "multiplicative"],
            },
            {
                "name": "seasonal_periods",
                "type": "choice",
                # The number of periods in this seasonality
                # (e.g. 7 periods for daily data would be used for weekly seasonality)
                "values": [4, 7, 10, 14, 24, 30],
                "value_type": "int",
                "is_ordered": True,
            },
        ]
        )


class LinearModelTest(TestCase):
    def test_fit_forecast(self):
        params = LinearModelParams(alpha=0.05)
        params.validate_params()
        m = LinearModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        m.predict(steps=30, freq="MS", include_history=True)
        m.plot()

        m_daily = LinearModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()

        m_daily.predict(steps=30, freq="D", include_history=True)
        m.plot()

    def test_others(self):
        params = LinearModelParams()
        params.validate_params()
        self.assertRaises(
            ValueError,
            LinearModel,
            TSData_multi,
            params,
        )

        m = LinearModel(TSData, params)

        # test __str__ method
        self.assertEqual(m.__str__(), "Linear Model")

        # test search space
        self.assertEqual(m.get_parameter_search_space(),
            [
            {
                "name": "alpha",
                "type": "choice",
                "value_type": "float",
                "values": [.01, .05, .1, .25],
                "is_ordered": True,
            },
        ]
        )


class QuadraticModelTest(TestCase):
    def test_fit_forecast(self):
        params = QuadraticModelParams()
        m = QuadraticModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        m.predict(steps=30, freq="MS", include_history=True)
        m.plot()

        m_daily = QuadraticModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()

        m_daily.predict(steps=30, freq="D", include_history=True)
        m.plot()

    def test_others(self):
        params = QuadraticModelParams()
        params.validate_params()
        self.assertRaises(
            ValueError,
            QuadraticModel,
            TSData_multi,
            params,
        )

        m = QuadraticModel(TSData, params)

        # test __str__ method
        self.assertEqual(m.__str__(), "Quadratic")

        # test search space
        self.assertEqual(m.get_parameter_search_space(),
            [
            {
                "name": "alpha",
                "type": "choice",
                "value_type": "float",
                "values": [.01, .05, .1, .25],
                "is_ordered": True,
            },
        ]
        )


class LSTMModelTest(TestCase):
    def test_fit_forecast(self):
        # use smaller time window and epochs for testing to reduce testing time
        params = LSTMParams(hidden_size=10, time_window=4, num_epochs=5)
        m = LSTMModel(data=TSData, params=params)
        m.fit()
        m.predict(steps=15)
        m.plot()

        m_daily = LSTMModel(data=TSData_daily, params=params)
        m_daily.fit()
        m_daily.predict(steps=30)
        m_daily.plot()


class SARIMAModelTest(TestCase):
    def test_fit_forecast(self):
        params = SARIMAParams(
            p=2,
            d=1,
            q=1,
            trend="ct",
            seasonal_order=(1, 0, 1, 12),
            enforce_invertibility=False,
            enforce_stationarity=False,
        )
        params.validate_params()
        m = SARIMAModel(TSData, params)
        m.fit(
            start_params=None,
            transformed=None,
            includes_fixed=None,
            cov_type=None,
            cov_kwds=None,
            method="lbfgs",
            maxiter=50,
            full_output=1,
            disp=False,
            callback=None,
            return_params=False,
            optim_score=None,
            optim_complex_step=None,
            optim_hessian=None,
            flags=None,
            low_memory=False,
        )
        m.predict(steps=30, freq="MS")
        m.plot()

        m_daily = SARIMAModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()

    def test_others(self):
        params = SARIMAParams(
            p=2,
            d=1,
            q=1,
            trend="ct",
            seasonal_order=(1, 0, 1, 12),
            enforce_invertibility=False,
            enforce_stationarity=False,
        )
        params.validate_params()
        m = SARIMAModel(TSData, params)

        # test search space
        self.assertEqual(m.get_parameter_search_space(),
            [
            {
                "name": "p",
                "type": "choice",
                "values": list(range(1, 6)),
                "value_type": "int",
                "is_ordered": True,
            },
            {
                "name": "d",
                "type": "choice",
                "values": list(range(1, 3)),
                "value_type": "int",
                "is_ordered": True,
            },
            {
                "name": "q",
                "type": "choice",
                "values": list(range(1, 6)),
                "value_type": "int",
                "is_ordered": True,
            },
            {
                "name": "seasonal_order",
                "type": "choice",
                "values": [(1, 0, 1, 7), (1, 0, 2, 7), (2, 0, 1, 7), (2, 0, 2, 7), (1, 1, 1, 7), (0, 1, 1, 7)],
                # Note: JSON representation must be 'int', 'float', 'bool' or 'str'.
                # so we use 'str' here instead of 'Tuple'
                # when doing HPT, we need to convert it back to tuple
                "value_type": "str",
            },
            {
                "name": "trend",
                "type": "choice",
                "values": ['n', 'c', 't', 'ct'],
                "value_type": "str",
            },
        ]
        )

        # test __str__ method
        self.assertEqual(m.__str__(), "SARIMA")

        # test input error
        self.assertRaises(
            ValueError,
            SARIMAModel,
            TSData_multi,
            params,
        )


class ProphetModelTest(TestCase):
    def test_fit_forecast(self):
        params = ProphetParams()
        m = ProphetModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        # adding cap and floor
        params = ProphetParams(cap=1000, floor=10, growth="logistic")
        m = ProphetModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        m_daily = ProphetModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()

        # add historical fit
        params = ProphetParams()
        m = ProphetModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS", include_history=True)
        m.plot()

        m_daily = ProphetModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D", include_history=True)
        m.plot()


        # test logistic growth with cap
        params = ProphetParams(growth="logistic", cap=1000)
        m = ProphetModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        params = ProphetParams(growth="logistic", cap=20)
        m_daily = ProphetModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()

        # Testing custom seasonalities.
        params = ProphetParams(
            custom_seasonalities=[
                {
                    "name": "monthly",
                    "period": 30.5,
                    "fourier_order": 5,
                },
            ],
        )
        params.validate_params()  # Validate params and ensure no errors raised.
        m = ProphetModel(TSData, params)
        m.fit()
        m.predict(steps=30, freq="MS")
        m.plot()

        params = ProphetParams(
            custom_seasonalities=[
                {
                    "name": "semi_annually",
                    "period": 365.25/2,
                    "fourier_order": 5,
                },
            ],
        )
        params.validate_params()  # Validate params and ensure no errors raised.
        m_daily = ProphetModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30, freq="D")
        m.plot()


class testVARModel(TestCase):
    def test_fit_forecast(self):
        params = VARParams()
        m = VARModel(TSData_multi, params)
        m.fit()
        m.predict(steps=30)


class testBayesianVARModel(TestCase):
    def test_fit_forecast(self):
        params = BayesianVARParams(p=3)
        m = BayesianVAR(TSData_multi, params)
        m.fit()
        m.predict(steps=30, include_history=True)
        m.plot()


class testEmpConfidenceInt(TestCase):
    def test_empConfInt_Prophet(self):
        params = ProphetParams(seasonality_mode="multiplicative")
        ci = EmpConfidenceInt(
            ALL_ERRORS, TSData, params, 50, 25, 12.5, ProphetModel, confidence_level=0.9
        )
        ci.get_eci(steps=100, freq="MS")


class testSTLFModel(TestCase):
    def test_fit_forecast(self):
        for method in ["theta", "prophet", "linear", "quadratic"]:
            params = STLFParams(m=12, method=method)
            m = STLFModel(TSData, params)
            m.fit()
            m.predict(steps=30)
            m.predict(steps=30, include_history=True)

        params = STLFParams(m=7, method="theta")
        m_daily = STLFModel(TSData_daily, params)
        m_daily.fit()
        m_daily.predict(steps=30)
        m.plot()

        m_daily.predict(steps=30, include_history=True)
        m.plot()

        # test when m > the length of time series
        params = STLFParams(m=10000, method="theta")
        self.assertRaises(
            ValueError,
            STLFModel,
            TSData_daily,
            params,
        )

    def test_others(self):
        # test param value error
        self.assertRaises(
            ValueError,
            STLFParams,
            method="random_model",
            m=12,
        )

        params = STLFParams(m=12, method="theta")
        params.validate_params()

        # test model param
        self.assertRaises(
            ValueError,
            STLFModel,
            TSData_multi,
            params,
        )

        # test __str__ method
        m = STLFModel(TSData, params)
        self.assertEqual(m.__str__(), "STLF")

class testNowcasting(TestCase):
    def test_LAG(self):
        self.assertEqual(list( LAG(pd.DataFrame(list(range(5)), columns = ['y']),1)['LAG_1'] )[1:], [0,1,2,3])

    def test_MOM(self):
        self.assertEqual( list( MOM(pd.DataFrame(list(range(5)), columns = ['y']),1)['MOM_1'][1:] ), [1,1,1,1])

    def test_MA(self):
        self.assertEqual( list( MA(pd.DataFrame(list(range(5)), columns = ['y']),1)['MA_1'] ), [0,1,2,3,4])

    def test_ROC(self):
        self.assertEqual( list( ROC(pd.DataFrame(list(range(5)), columns = ['y']),1)['ROC_1'] )[1:], [0,0,0,0])

    def test_MACD(self):
        error_threshold = 0.0001
        target = np.array([7.770436585431938, 7.913716315475984, 8.048858332839053, 8.176225524209826])
        error1 = np.sum( np.array( MACD(pd.DataFrame(list(range(30)), columns = ['y']),1)[-4:]['MACD_1_21'] ) - target )
        self.assertLessEqual(error1, error_threshold,'MACD_1_21 produces errors!')

        target = [7.37176002981048, 7.496954620458209, 7.620613089998056, 7.742177915869659]
        error2 = np.sum(np.abs(MACD(pd.DataFrame(list(range(30)), columns = ['y']),1)[-4:]['MACDsign_1_21'] - target))
        self.assertLessEqual(error2, error_threshold,'MACDsign_1_21 produces errors!')

        target = [0.3986765556214573, 0.41676169501777505, 0.4282452428409975, 0.4340476083401672]
        error3 = np.sum(np.abs(MACD(pd.DataFrame(list(range(30)), columns = ['y']),1)[-4:]['MACDdiff_1_21'] - target))
        self.assertLessEqual(error3, error_threshold,'MACDdiff_1_21 produces errors!')

class testHarmonicRegression(TestCase):
    def setUp(self):
        times = pd.to_datetime(
            np.arange(start=1576195200, stop=1577836801, step=60 * 60), unit="s"
        )
        self.series_times = pd.Series(times)
        harms = HarmonicRegressionModel.fourier_series(self.series_times, 24, 3)
        self.harms_sum = np.sum([1, 1, 1, 1, 1, 1] * harms, axis=1)
        self.data = TimeSeriesData(
            pd.DataFrame({"time": self.series_times, "values": self.harms_sum})
        )

        self.params = HarmonicRegressionParams(24, 3)

    def test_fit_and_predict(self):
        hrm = HarmonicRegressionModel(self.data, self.params)
        hrm.fit()
        self.assertIsNotNone(hrm.params)
        self.assertIsNotNone(hrm.harms)

        preds = hrm.predict(self.series_times.head(1))
        self.assertAlmostEqual(preds["fcst"][0], self.harms_sum[0], delta=0.0001)


class TestParameterTuningDefaultSearchSpace(TestCase):
    def test_parameter_tuning_default_search_space_arima(self):
        search_space = ARIMAModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_prophet(self):
        search_space = ProphetModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_linear_model(self):
        search_space = LinearModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_quadratic_model(self):
        search_space = QuadraticModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_sarima_model(self):
        search_space = SARIMAModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_holtwinters_model(self):
        search_space = HoltWintersModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_var_model(self):
        self.assertRaises(NotImplementedError, VARModel.get_parameter_search_space)

    def test_parameter_tuning_default_search_space_theta_model(self):
        search_space = ThetaModel.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)

    def test_parameter_tuning_default_search_space_arnet_model(self):
        search_space = ARNet.get_parameter_search_space()
        TimeSeriesParameterTuning.validate_parameters_format(search_space)


if __name__ == "__main__":
    unittest.main()
