import plotly.express as px
def heatmap(frame,**kwargs): return px.imshow(frame.select_dtypes("number").corr(),text_auto=True,**kwargs)

