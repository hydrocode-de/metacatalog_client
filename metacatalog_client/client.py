from pydantic import BaseModel, Field, field_validator
from pydantic import HttpUrl
import httpx


class Client(BaseModel):
    url: HttpUrl = "http://localhost:8001/"
    host_version: str = Field(default=None, init=False)
    _static_info: dict = Field(default={}, init=False, repr=False)

    @field_validator("url", mode="before")
    def validate_url(cls, url):
        if not url.endwith("/"):
            url += "/"
        return url

    def model_post_init(self, __context):
        try:
            response = httpx.get(f"{self.url}version")
            version = response.json()
            self.host_version = version["metacatalog_api"]
        except httpx.ConnectError:
            raise ValueError(
                f"the MetaCatalog host at {self.url} is not reachable. Please check the URL."
            )
        except KeyError:
            raise ValueError(
                f"The host at {self.url}version did not response with a valid 'metacatalog_api' version."
            )

    def set_static(self, author: int | dict = None, license: int | dict = None):
        """
        """
        if author is not None:
            self._static_info.update(author=author)
        if license is not None:    
            self._static_info.update(license=license)
    
    def reset_static(self):
        self._static_info = {}

    def authors(self, limit: int = 10):
        response = httpx.get(f"{self.url}authors.json", params=dict(limit=limit))
        return response.json()

    def licenses(self, limit: int = None):
        response = httpx.get(f"{self.url}licenses.json", params=dict(limit=limit))
        return response.json()
    
    def variables(self, limit: int = None):
        response = httpx.get(f"{self.url}variables.json", params=dict(limit=limit))
        return response.json()

    def entries(self, limit: int = 10):
        response = httpx.get(f"{self.url}entries.json", params=dict(limit=limit))
        return response.json()

    def search(self, prompt: str, limit: int = 10):
        params = dict(search=prompt, limit=limit, full_text=True)
        response = httpx.get(f"{self.url}entries.json", params=params)
        return response.json()

    def entry(self, entry_id: str):
        response = httpx.get(f"{self.url}entries/{entry_id}.json")
        return response.json()

    def create_entry(
        self,
        title: str,
        abstract: str,
        variable: int | dict,
        author: int | dict | None = None,
        license: int | dict | None = None,
        keywords: list[int] = [],
        datasource: None | dict = None,
        external_id: None | str = None,
        embargo: bool = False,
        citation: None | str = None,
        comment: None | str = None,
        **kwargs,
    ):
        # the author or license can be set as a static property to this instance
        if 'author' in self._static_info:
            author = self._static_info['author']
        if 'license' in self._static_info:
            license = self._static_info['license']
        
        if author is None:
            raise ValueError("author must be set")
        if license is None:
            raise ValueError("license must be set")
        
        details = [dict(key=k, value=v) for k, v in kwargs.items()]
        
        payload = dict(
            title=title,
            abstract=abstract,
            external_id=external_id,
            citation=citation,
            comment=comment,
            keywords=keywords,
            embargo=embargo,
            author=author,
            license=license,
            datasource=datasource,
            variable=variable,
            details=details
        )

        response = httpx.post(f"{self.url}entries", json=payload)
        return response.json()
