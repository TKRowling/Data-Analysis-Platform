import plotly.express as px
def line_chart(frame,x,y=None,color=None,**kwargs): return px.line(frame,x=x,y=y,color=color,**kwargs)

