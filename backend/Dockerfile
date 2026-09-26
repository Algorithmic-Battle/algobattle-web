FROM python:3.14

WORKDIR /code
COPY . .
RUN pip install .
RUN cd .. && rm -r code

CMD ["uvicorn", "algobattle_web.app:app", "--host", "0.0.0.0", "--port", "8000"]
