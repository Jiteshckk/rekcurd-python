#!/usr/bin/python
# -*- coding: utf-8 -*-


from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import List, Tuple, Generator

from .utils import RekcurdConfig, PredictInput, PredictResult, EvaluateResult, EvaluateDetail, EvaluateResultDetail
from .logger import SystemLoggerInterface, ServiceLoggerInterface, JsonSystemLogger, JsonServiceLogger
from .data_servers import DataServer


class Rekcurd(metaclass=ABCMeta):
    """
    Rekcurd
    """
    _system_logger: SystemLoggerInterface = None
    _service_logger: ServiceLoggerInterface = None
    config: RekcurdConfig = None
    data_server: DataServer = None
    predictor: object = None

    @abstractmethod
    def load_model(self, filepath: str) -> object:
        """
        load_model
        :param filepath: ML model file path. str
        :return predictor: Your ML predictor object. object
        """
        raise NotImplemented()

    @abstractmethod
    def predict(self, predictor: object, idata: PredictInput, option: dict = None) -> PredictResult:
        """
        predict
        :param predictor: Your ML predictor object. object
        :param idata: Input data. PredictInput, one of string/bytes/arr[int]/arr[float]/arr[string]
        :param option: Miscellaneous. dict
        :return result: Result. PredictResult
            result.label: Label. One of string/bytes/arr[int]/arr[float]/arr[string]
            result.score: Score. One of float/arr[float]
            result.option: Miscellaneous. dict
        """
        raise NotImplemented()

    @abstractmethod
    def evaluate(self, predictor: object, filepath: str) -> Tuple[EvaluateResult, List[EvaluateResultDetail]]:
        """
        evaluate
        :param predictor: Your ML predictor object. object
        :param filepath: Evaluation data file path. str
        :return result: Result. EvaluateResult
            result.num: Number of data. int
            result.accuracy: Accuracy. float
            result.precision: Precision. arr[float]
            result.recall: Recall. arr[float]
            result.fvalue: F1 value. arr[float]
            result.option: Optional metrics. dict[str, float]
        :return detail[]: Detail result of each prediction. List[EvaluateResultDetail]
            detail[].result: Prediction result. PredictResult
            detail[].is_correct: Prediction result is correct or not. bool
        """
        raise NotImplemented()

    @abstractmethod
    def get_evaluate_detail(self, filepath: str, details: List[EvaluateResultDetail]) -> Generator[EvaluateDetail, None, None]:
        """
        get_evaluate_detail
        :param filepath: Evaluation data file path. str
        :param details: Detail result of each prediction. List[EvaluateResultDetail]
        :return rtn: Return results. Generator[EvaluateDetail, None, None]
            rtn.input: Input data. PredictInput, one of string/bytes/arr[int]/arr[float]/arr[string]
            rtn.label: Predict label. PredictLabel, one of string/bytes/arr[int]/arr[float]/arr[string]
            rtn.result: Predict detail. EvaluateResultDetail
        """
        raise NotImplemented()

    @property
    def system_logger(self):
        return self._system_logger

    @system_logger.setter
    def system_logger(self, system_logger: SystemLoggerInterface):
        if isinstance(system_logger, SystemLoggerInterface):
            self._system_logger = system_logger
        else:
            raise TypeError("Invalid system_logger type.")

    @property
    def service_logger(self):
        return self._service_logger

    @service_logger.setter
    def service_logger(self, service_logger: ServiceLoggerInterface):
        if isinstance(service_logger, ServiceLoggerInterface):
            self._service_logger = service_logger
        else:
            raise TypeError("Invalid service_logger type.")

    def load_config_file(self, config_file: str):
        self.config = RekcurdConfig(config_file)

    def run(self, host: str = None, port: int = None, max_workers: int = None, **options):
        import grpc
        import time
        from concurrent import futures
        from rekcurd.protobuf import rekcurd_pb2_grpc
        from rekcurd import RekcurdDashboardServicer, RekcurdWorkerServicer

        if self.config is None:
            self.config = RekcurdConfig()
        if port and "service_port" in options:
            options["service_port"] = port
        self.config.set_configurations(**options)

        self.data_server = DataServer(self.config)
        if self._system_logger is None:
            self._system_logger = JsonSystemLogger(config=self.config)
        if self._service_logger is None:
            self._service_logger = JsonServiceLogger(config=self.config)
        _host = "127.0.0.1"
        _port = 5000
        _max_workers = 1
        host = host or _host
        port = int(port or self.config.SERVICE_PORT or _port)
        max_workers = int(max_workers or _max_workers)

        self.predictor = self.load_model(self.data_server.get_model_path())
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        rekcurd_pb2_grpc.add_RekcurdDashboardServicer_to_server(
            RekcurdDashboardServicer(app=self), server)
        rekcurd_pb2_grpc.add_RekcurdWorkerServicer_to_server(
            RekcurdWorkerServicer(app=self), server)
        server.add_insecure_port("{0}:{1}".format(host, port))
        self.system_logger.info("Start rekcurd worker on {0}:{1}".format(host, port))
        server.start()
        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
            self.system_logger.info("Shutdown rekcurd worker.")
            server.stop(0)

    # TODO: DEPRECATED BELOW
    __type_input = None
    __type_output = None

    def set_type(self, type_input: Enum, type_output: Enum) -> None:
        self.__type_input = type_input
        self.__type_output = type_output

    def get_type_input(self) -> Enum:
        return self.__type_input

    def get_type_output(self) -> Enum:
        return self.__type_output
