import gradio as gr


def say_hello(name):
    return f"Hello {name}!"


interface = gr.Interface(fn=say_hello, inputs="text", outputs="text")
interface.launch()
