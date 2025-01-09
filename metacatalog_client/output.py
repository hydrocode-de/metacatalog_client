from typing import Any
from abc import ABC, abstractmethod
import warnings

from pydantic import BaseModel
from httpx import Response

class Output(BaseModel, ABC):
    @abstractmethod
    def parse(self, response: Response) -> Any:
        pass

    def __call__(self, response: Response) -> Any:
        return self.parse(response=response)


class JSONOutput(Output):
    wrap_lists: bool = False
    
    def parse(self, response):
        out = response.json()
        if self.wrap_lists and isinstance(out, (list, tuple)):
            return {
                'count': len(out),
                'items': out
            }
        else:
            return out


class CSVOutput(Output):
    with_header: bool = True

    def parse(self, response):
        out = response.json()
        if isinstance(out, dict):
            out = [out]
        if len(out) == 0:
            return ""
        elif not all(isinstance(d, dict) for d in out):
            warnings.warn("Cannot parse CSV, as not every object in the response list is a dict.")
            return out[0]

        def header_parser(d: dict, prefix: str = "") -> list[str]:
            headers = []
            for k, v in d.items():
                if isinstance(v, dict):
                    child_header = header_parser(v, prefix=f"{prefix}{k}.")
                    headers.extend(child_header)
                else:
                    headers.append(f"{prefix}{k}")
            return headers

        def level_parser(d: dict) -> list[str]:
            body = []
            for k, v in d.items():
                if isinstance(v, dict):
                    body.extend(level_parser(v))
                else:
                    body.append(str(v))
            return body
                    
        body = list(map(level_parser, out))
        if self.with_header:
            header = header_parser(out[0])
            csv = ",".join(header) + "\n"
        else:
            csv = ""
        csv += "\n".join([",".join(line) for line in body])
        return csv

