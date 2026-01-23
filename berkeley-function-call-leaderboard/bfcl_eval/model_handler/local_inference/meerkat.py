from bfcl_eval.model_handler.local_inference.base_oss_handler import OSSHandler
from overrides import override

class MeerkatHandler(OSSHandler):
    """
    Handler for the Zoho Meerkat-7B-DPO model.
    """

    def __init__(self, model_name, temperature, **kwargs) -> None:
        super().__init__(model_name, temperature, **kwargs)


    @override
    def _format_prompt(self, messages, function):
        """
        Formats the prompt according to the Meerkat chat template:
        "{% for message in messages %}{{'<|im_start|>' + message['role'] | capitalize + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>Assistant\n' }}{% endif %}"
        """
        formatted_prompt = ""

        for message in messages:
            role = message['role'].capitalize()
            content = message['content']
            formatted_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"

        formatted_prompt += "<|im_start|>Assistant\n"

        return formatted_prompt
