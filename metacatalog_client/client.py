from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator
from pydantic import HttpUrl
import httpx

from .output import Output, JSONOutput, CSVOutput

MIN_HOST_VERSION = "0.3.8"

class Client(BaseModel):
    url: HttpUrl = "http://localhost:8001/"
    host_version: str = Field(default=None, init=False)
    static_info: dict = Field(default={}, init=False, repr=False)

    output: Output = Field(default_factory=JSONOutput)

    @field_validator("url", mode="before")
    def validate_url(cls, url):
        if not url.endswith("/"):
            url += "/"
        return url

    @field_validator("output", mode="before")
    @classmethod
    def validate_output(cls, output):
        if isinstance(output, Output):
            return output
        if output.lower() == "json":
            return JSONOutput()
        elif output.lower() == "csv":
            return CSVOutput()
        else:
            raise ValueError(f"{output} is not a valid output format")
        
    def model_post_init(self, __context):
        try:
            response = httpx.get(f"{self.url}version")
            version = response.json()
            self.host_version = version["metacatalog_api"]
        except httpx.ConnectError:
            raise ValueError(
                f"The MetaCatalog host at {self.url} is not reachable. Please check the URL."
            )
        except KeyError:
            raise ValueError(
                f"The host at {self.url}version did not response with a valid 'metacatalog_api' version."
            )

        if self.host_version < MIN_HOST_VERSION:
            raise RuntimeError(f"The host at {self.url} runs on version: '{self.host_version}', but this client requires at least version: '{MIN_HOST_VERSION}'")

    def _sanitize_params(self, **params: dict) -> dict:
        return {k: v for k, v in params.items() if v is not None}

    def _sanitize_json(self, **params: dict) -> dict:
        def serializer(val):
            if isinstance(val, dict):
                return {k: serializer(v) for k, v in val.items() if v is not None}
            elif isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, timedelta):
                return f"P{val.days}DT{val.total_seconds()}S"
            return val
        
        return {k: serializer(v) for k, v in params.items() if v is not None}

    def set_static(self, author: int | dict = None, license: int | dict = None):
        """
        """
        if author is not None:
            self.static_info.update(author=author)
        if license is not None:    
            self.static_info.update(license=license)
    
    def reset_static(self):
        self.static_info = {}

    def authors(self, search: str = None, limit: int = 10):
        response = httpx.get(f"{self.url}authors.json", params=self._sanitize_params(limit=limit, search=search))
        return self.output.parse(response)

    def author(self, id: int, name: str = None) -> dict:
        if id is not None:
            response = httpx.get(f"{self.url}authors/{id}.json")
            return response.json()
        elif name is not None:
            response = httpx.get(f"{self.url}author.json", params=self._sanitize_params(name=name))
            return response.json()

    def licenses(self, limit: int = None):
        response = httpx.get(f"{self.url}licenses.json", params=self._sanitize_params(limit=limit))
        return self.output.parse(response=response)
    
    def variables(self, only_available: bool = False, limit: int = None):
        response = httpx.get(f"{self.url}variables.json", params=self._sanitize_params(limit=limit, only_available=only_available))
        return self.output.parse(response=response)

    def variable(self, id: int) -> dict:
        if self.host_version > '0.3.8':
            url = f"{self.url}variables/{id}.json"
        else:
            url = f"{self.url}variable/{id}.json"
        response = httpx.get(url)
        return response.json()

    def entries(self, title: str = None, description: str = None, variable: str = None, limit: int = 10, offset: int = 0):
        params = self._sanitize_params(title=title, description=description, variable=variable, limit=limit, offset=offset)
        response = httpx.get(f"{self.url}entries.json", params=params)
        return self.output.parse(response=response)

    def search(self, prompt: str, limit: int = 10):
        params = self._sanitize_params(search=prompt, limit=limit, full_text=True)
        response = httpx.get(f"{self.url}entries.json", params=params)
        return self.output.parse(response=response)
    
    def entry(self, entry_id: int):
        response = httpx.get(f"{self.url}entries/{entry_id}.json")
        return response.json()
    
    def group_types(self):
        response = httpx.get(f"{self.url}group-types.json")
        return self.output.parse(response=response)
    
    def groups(self, title: str = None, description: str = None, type: str = None, limit: int = None, offset: int = None):
        params = self._sanitize_params(title=title, description=description, type=type, limit=limit, offset=offset)
        response = httpx.get(f"{self.url}groups.json", params=params)
        return self.output.parse(response=response)
    
    def group(self, id: int):
        response = httpx.get(f"{self.url}groups/{id}.json")
        return response.json()

    def create_entry(
        self,
        title: str,
        abstract: str,
        variable: int | dict,
        author: int | dict | None = None,
        location: None | str | dict = None,
        license: int | dict | None = None,
        keywords: list[int] = [],
        datasource: None | dict = None,
        external_id: None | str = None,
        embargo: bool = False,
        citation: None | str = None,
        comment: None | str = None,
        details: list[dict] = [],
        groups: list[int | dict] = [],
        duplicate_authors: bool = False,
        **kwargs,
    ):
        # the author or license can be set as a static property to this instance
        if 'author' in self.static_info:
            author = self.static_info['author']
        if 'license' in self.static_info:
            license = self.static_info['license']
        
        if author is None:
            raise ValueError("author must be set")
        if license is None:
            raise ValueError("license must be set")
        
        details = [*details, *[dict(key=k, value=v) for k, v in kwargs.items()]]
        
        payload = dict(
            title=title,
            abstract=abstract,
            external_id=external_id,
            citation=citation,
            comment=comment,
            location=location,  
            keywords=keywords,
            embargo=embargo,
            author=author,
            license=license,
            datasource=datasource,
            variable=variable,
            details=details,
            groups=groups
        )

        response = httpx.post(
            f"{self.url}entries", 
            json=self._sanitize_json(**payload), 
            params=self._sanitize_params(duplicate_authors=duplicate_authors)
        )
        return response.json()
