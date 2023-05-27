FROM python:3.10
WORKDIR /code
ADD . .
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
CMD ["python", "apiserver.py"]