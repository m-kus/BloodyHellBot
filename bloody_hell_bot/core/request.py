class BloodyHellRequest:

    def __init__(self, message: dict):
        self.msg = message

    @property
    def user_id(self):
        return self.msg['from']['id']

    @property
    def msg_type(self):
        if 'message' in self.msg:
            return 'callback_query'
        if 'document' in self.msg:
            return 'document'
        if 'photo' in self.msg:
            return 'photo'
        return 'text'

    @property
    def msg_id(self):
        return self.msg['message']['message_id']

    @property
    def msg_text(self):
        return self.msg['message']['text']

    @property
    def parameters(self):
        return self.msg['data'].split('_')
