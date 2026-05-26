from typing import List, Optional
from api.client import ApiClient
from models.movie import Movie, MovieCreate, MovieUpdate


class MoviesApi:
    def __init__(self, client: ApiClient):
        self.client = client

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Movie]:
        result = self.client.get("/movies", params={"skip": skip, "limit": limit})
        return [Movie(**m) for m in result]

    def get_by_id(self, movie_id: int) -> Movie:
        result = self.client.get(f"/movies/{movie_id}")
        return Movie(**result)

    def create(self, movie: MovieCreate) -> Movie:
        result = self.client.post("/movies", json=movie.model_dump(exclude_none=True))
        return Movie(**result)

    def update(self, movie_id: int, movie: MovieUpdate) -> Movie:
        result = self.client.put(f"/movies/{movie_id}", json=movie.model_dump(exclude_none=True))
        return Movie(**result)

    def delete(self, movie_id: int) -> None:
        self.client.delete(f"/movies/{movie_id}")
