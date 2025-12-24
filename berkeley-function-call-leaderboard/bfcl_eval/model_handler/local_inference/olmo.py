from bfcl_eval.model_handler.local_inference.base_oss_handler import OSSHandler
from overrides import override

class OLMoHandler(OSSHandler):
    """
    Handler for the AllenAI OLMo 2 model series.
    """

    def __init__(self, model_name, temperature) -> None:
        super().__init__(model_name, temperature)

    @override
    def _format_prompt(self, messages, function):
        """
        Formats the prompt according to the OLMo 2 chat template.
        Template:
        {{- bos_token -}}
        {%- for message in messages -%}
            {%- if message["role"] == "system" -%}
                {{- "<|system|>\n" + message["content"] + "\n" -}}
            {%- elif message["role"] == "user" -%}
                {{- "<|user|>\n" + message["content"] + "\n" -}}
            {%- elif message["role"] == "assistant" -%}
                {%- if not loop.last -%}
                    {{- "<|assistant|>\n" + message["content"] + eos_token + "\n" -}}
                {%- else -%}
                    {{- "<|assistant|>\n" + message["content"] + eos_token -}}
                {%- endif -%}
            {%- endif -%}
            {%- if loop.last and add_generation_prompt -%}
                {{- "<|assistant|>\n" -}}
            {%- endif -%}
        {%- endfor -%}
        """
        
        bos_token = self.tokenizer.bos_token
        eos_token = self.tokenizer.eos_token
        
        formatted_messages = []
        for i, message in enumerate(messages):
            role = message["role"]
            content = message["content"]

            if role == "system":
                formatted_messages.append(f"<|system|>\n{content}\n")
            elif role == "user":
                formatted_messages.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                if i < len(messages) - 1:
                    formatted_messages.append(f"<|assistant|>\n{content}{eos_token}\n")
                else:
                    formatted_messages.append(f"<|assistant|>\n{content}{eos_token}")

        prompt = bos_token + "".join(formatted_messages) + "<|assistant|>\n"
        
        return prompt