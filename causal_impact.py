import io
import os
import tempfile
import flask
from flask import Response
import googleapiclient.discovery
import google_auth
import google_sheets
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from causalimpact import CausalImpact
import numpy as np

app = flask.Blueprint('causal_impact', __name__)

# SOURCE https://github.com/dafiti/causalimpact/blob/master/causalimpact/plot.py
def create_ci_plot(ci, post_period, pre_period):
    panels = ['original', 'pointwise', 'cumulative']
    figsize=(15, 12)
    fig = plt.figure(figsize=figsize)
    # First points can be noisy due approximation techniques used in the likelihood
    # optimizaion process. We remove those points from the plots.
    llb = ci.trained_model.filter_results.loglikelihood_burn
    inferences = ci.inferences.iloc[llb:]
    intervention_idx = inferences.index.get_loc(ci.post_period[0])
    n_panels = len(panels)
    ax = plt.subplot(n_panels, 1, 1)
    idx = 1
    print('I am ok!')
    if 'original' in panels:
        ax.plot(pd.concat([ci.pre_data.iloc[llb:, 0], ci.post_data.iloc[:, 0]]),
                    'k', label='y')
        ax.plot(inferences['preds'], 'b--', label='Predicted')
        ax.axvline(inferences.index[intervention_idx - 1], c='k', linestyle='--')
        ax.fill_between(
            ci.pre_data.index[llb:].union(ci.post_data.index),
            inferences['preds_lower'],
            inferences['preds_upper'],
            facecolor='blue',
            interpolate=True,
            alpha=0.25
        )
        ax.grid(True, linestyle='--')
        ax.legend()
        if idx != n_panels:
            plt.setp(ax.get_xticklabels(), visible=False)
        idx += 1

    if 'pointwise' in panels:
        ax = plt.subplot(n_panels, 1, idx, sharex=ax)
        ax.plot(inferences['point_effects'], 'b--', label='Point Effects')
        ax.axvline(inferences.index[intervention_idx - 1], c='k', linestyle='--')
        ax.fill_between(
            inferences['point_effects'].index,
            inferences['point_effects_lower'],
            inferences['point_effects_upper'],
            facecolor='blue',
            interpolate=True,
            alpha=0.25
        )
        ax.axhline(y=0, color='k', linestyle='--')
        ax.grid(True, linestyle='--')
        ax.legend()
        if idx != n_panels:
            plt.setp(ax.get_xticklabels(), visible=False)
        idx += 1

    if 'cumulative' in panels:
        ax = plt.subplot(n_panels, 1, idx, sharex=ax)
        ax.plot(inferences['post_cum_effects'], 'b--', label='Cumulative Effect')
        ax.axvline(inferences.index[intervention_idx - 1], c='k', linestyle='--')
        ax.fill_between(
            inferences['post_cum_effects'].index,
            inferences['post_cum_effects_lower'],
            inferences['post_cum_effects_upper'],
            facecolor='blue',
            interpolate=True,
            alpha=0.25
        )
        ax.grid(True, linestyle='--')
        ax.axhline(y=0, color='k', linestyle='--')
        ax.legend()
    # Alert if points were removed due to loglikelihood burning data
    if llb > 0:
        text = ('Note: The first {} observations were removed due to approximate '
                    'diffuse initialization.'.format(llb))
        fig.text(0.1, 0.01, text, fontsize='large')
    
    return fig

@app.route('/causal-impact')
def causal_impact():
    if google_auth.is_logged_in():
        return flask.render_template("causalimpact.html", title='Causal Impact Graph', user_info=google_auth.get_user_info())
        
    return flask.render_template('index.html')

@app.route('/causal-impact-graph.png')
def fig():
    df = google_sheets.gsheet2df()
    df['Revenue'] = df['Revenue'].apply(lambda x: float(x))
    del df['Date']
    df = df.set_index(pd.date_range(start='20191201', periods=len(df)))
    pre_period = ['20191201', '20200314']
    post_period = ['20200315', '20200409']
    ci = CausalImpact(df, pre_period, post_period)
    fig = create_ci_plot(ci, post_period, pre_period)
    #img = io.BytesIO()
    #fig.savefig(img)
    #img.seek(0)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")
    #return flask.send_file(img, mimetype='image/png')

@app.route('/return-causal-impact-image')
def return_files_tut():
    filename = flask.safe_join(app.root_path, "/causal-impact-graph.png")
    print(filename)
    try:
        return flask.send_from_directory(directory=filename,filename='causal-impact-graph.png')
    except Exception as e:
        return str(e)