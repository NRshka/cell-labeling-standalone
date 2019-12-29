from enum import Enum

ErrCodes = Enum('ErrCodes', 'WRONG_ID WRONG_CODE NO_CODE NO_ID WRONG_PACKET')
ReqCodes = Enum('ReqCodes', 'GET_ID NEW_IMAGES SUCCESS GET_NN_PREDICTION')

saveMetafiles: bool = False

client_config = {
    'url': "http://localhost:4000/jsonrpc",
    'headers': {'content-type': 'application/json'}
}