import plotly.express as px
def pie_chart(frame,names,values=None,**kwargs): return px.pie(frame,names=names,values=values,**kwargs)

