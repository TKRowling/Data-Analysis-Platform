import plotly.express as px
def bar_chart(frame,x,y=None,color=None,**kwargs): return px.bar(frame,x=x,y=y,color=color,**kwargs)

