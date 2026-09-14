from fastapi import HTTPException

class DataQualityException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)

class MarketDataException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=502, detail=detail)
