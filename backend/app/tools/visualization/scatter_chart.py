import plotly.express as px
def scatter_chart(frame,x,y,color=None,**kwargs): return px.scatter(frame,x=x,y=y,color=color,**kwargs)

