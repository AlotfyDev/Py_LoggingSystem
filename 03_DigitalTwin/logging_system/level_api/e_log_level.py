from __future__ import annotations

from enum import Enum


class ELogLevel(str, Enum):
    ERR = "ERROR"
    Debug = "DEBUG"
    Info = "INFO"
    Fatal = "FATAL"
    Trace = "TRACE"
    Warn = "WARN"

    @property
    def runtime_level(self) -> str:
        return self.value

    @classmethod
    def parse(cls, value: str) -> "ELogLevel":
        current = str(value).strip()
        if current == "":
            raise ValueError("log level value is required")
        normalized = current.upper()
        mapping = {
            "ERR": cls.ERR,
            "ERROR": cls.ERR,
            "DEBUG": cls.Debug,
            "INFO": cls.Info,
            "FATAL": cls.Fatal,
            "TRACE": cls.Trace,
            "WARN": cls.Warn,
            "WARNING": cls.Warn,
        }
        if normalized not in mapping:
            raise ValueError(f"unsupported level: {value}")
        return mapping[normalized]
