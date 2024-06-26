import boto3
import os
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from uuid import uuid4
from getSignedUrl import getSignedUrl

load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logger.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))

@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):

    logger.info(f"Title : {post.title}")
    logger.info(f"Content: {post.body}")
    logger.info(f"UserId : {authorization}")
    post_id = uuid4()

    data = table.put_item(Item={"UserId": f"USERID#{authorization}",
                "PostId": f"POSTID#{post_id}",
                "Title": f"{post.title}",
                "Content": f"{post.body}"})
    # Doit retourner le résultat de la requête la table dynamodb
    return data

@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    if user==None:
        response = table.scan(
            Select='ALL_ATTRIBUTES',
            ReturnConsumedCapacity='TOTAL',
        )
        items = response["Items"]
    else:
        response = table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression="#UserId = :userid",
            ExpressionAttributeValues={
                ":userid": f"USERID#{user}",
            },
            ExpressionAttributeNames={ "#UserId": "userid" },
        )
        items = response["Items"]
    # Doit retourner une liste de post
    return items

    
@app.delete("/posts/{post_id}")
async def get_post_user_id(post_id: str):#je suppose que c'est la fonction pour supprimer un post 
    #mais étant donné que je ne suis pas sûr que ce soit bien ça j'ai codé une fonction qui à un post_id renvoie le post en entier
    resp = table.query(
        Select='ALL_ATTRIBUTES',
        KeyConditionExpression="#PostId = :postid",
        ExpressionAttributeValues={
            ":postid": f"POSTID#{post_id}",
        },
        ExpressionAttributeNames={ "#PostId": "postid" },
    )
    items = resp["Items"]
    # Doit retourner le résultat de la requête la table dynamodb
    return items

@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str,filetype: str, postId: str,authorization: str | None = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

