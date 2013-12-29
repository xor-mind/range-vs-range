"""
The main pages for the site
"""
from flask import render_template, redirect, url_for
from rvr import APP
from rvr.forms.change import ChangeForm
from rvr.core.api import API, APIError
from rvr.app import AUTH
from rvr.core.dtos import LoginRequest, ChangeScreennameRequest
from werkzeug.exceptions import abort  # @UnresolvedImport
import logging
from flask.helpers import flash
from flask.globals import request, session, g
from rvr.forms.action import action_form
from rvr.core import dtos

@APP.before_request
def ensure_user():
    """
    Commit user to database and determine userid
    """
    if not g.user or 'identity' not in g.user:
        # user is not authenticated yet
        return
    if 'userid' in session and 'screenname' in session:
        # user is authenticated and authorised (logged in)
        return
    if 'screenname' in session:
        # user had changed screenname but not yet logged in
        screenname = session['screenname']
    else:
        # regular login
        screenname = g.user.name
    api = API()
    req = LoginRequest(identity=g.user.identity,  # @UndefinedVariable
                       email=g.user.email,  # @UndefinedVariable
                       screenname=screenname)  # @UndefinedVariable
    result = api.login(req)
    if result == API.ERR_LOGIN_DUPLICATE_SCREENNAME:
        session['screenname'] = g.user.name
        # User is authenticated with OpenID, but not yet authorised (logged
        # in). We redirect them to a page that allows them to choose a
        # different screenname.
        flash("The screenname '%s' is already taken." % screenname)
        if request.endpoint != 'change_screenname':
            return redirect(url_for('change_screenname'))
    elif isinstance(result, APIError):
        logging.debug("login error: %s", result)
        abort(403)
    else:
        session['screenname'] = result.screenname
        session['userid'] = result.userid

@APP.route('/change', methods=['GET','POST'])
@AUTH.required
def change_screenname():
    """
    Without the user being logged in, give the user the option to change their
    screenname from what Google OpenID gave us.
    """
    form = ChangeForm()
    if form.validate_on_submit():
        new_screenname = form.change.data
        session['screenname'] = new_screenname
        if 'userid' in session:
            req = ChangeScreennameRequest(session['userid'],
                                          session['screenname'])
            resp = API().change_screenname(req)
            if isinstance(resp, APIError):
                logging.debug("change_screenname error: %s", resp)
                flash("An error occurred.")
            else:
                flash("Your screenname has been changed to '%s'." %
                      (new_screenname, ))
        return redirect(url_for('home_page'))
    screenname = session['screenname'] if 'screenname' in session  \
        else g.user.name
    return render_template('change.html', title='Change Your Screenname',
                           current=screenname, form=form)

@APP.route('/', methods=['GET'])
def landing_page():
    """
    Generates the unauthenticated landing page. AKA the main or home page.
    """
    return render_template('landing.html', title='Welcome')

@APP.route('/home', methods=['GET'])
@AUTH.required
def home_page():
    """
    Authenticated landing page. User is taken here when logged in.
    """
    api = API()
    userid = session['userid']
    screenname = session['screenname']
    open_games = api.get_open_games()
    if isinstance(open_games, APIError):
        flash("An unknown error occurred retrieving your open games.")
        return redirect(url_for("landing_page"))
    my_games = api.get_user_games(userid)
    if isinstance(my_games, APIError):
        flash("An unknown error occurred retrieving your running games.")
        return redirect(url_for("landing_page"))
    my_open = [og for og in open_games
               if any([u.userid == userid for u in og.users])]
    others_open = [og for og in open_games
                   if not any([u.userid == userid for u in og.users])]
    my_turn_games = [mg for mg in my_games.running_details
                     if mg.current_user_details.userid == userid]
    others_turn_games = [mg for mg in my_games.running_details
                         if mg.current_user_details.userid != userid]
    return render_template('home.html', title='Home',
        screenname=screenname,
        my_open=my_open,
        others_open=others_open,
        my_turn_games=my_turn_games,
        others_turn_games=others_turn_games
        )

@APP.route('/join', methods=['GET'])
@AUTH.required
def join_game():
    """
    Join game, flash status, redirect back to /home
    """
    api = API()
    gameid = request.args.get('gameid', None)
    if gameid is None:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    try:
        gameid = int(gameid)
    except ValueError:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    userid = session['userid']
    response = api.join_game(userid, gameid)
    if response is api.ERR_JOIN_GAME_ALREADY_IN:
        msg = "You are already registered in game %s." % (gameid,)
    elif response is api.ERR_JOIN_GAME_GAME_FULL:
        msg = "Game %s is full." % (gameid,)
    elif response is api.ERR_NO_SUCH_OPEN_GAME:
        msg = "Invalid game ID."
    elif isinstance(response, APIError):
        msg = "An unknown error occurred."
    else:
        msg = "You have joined game %s." % (gameid,)
    flash(msg)
    return redirect(url_for('home_page'))

@APP.route('/leave', methods=['GET'])
@AUTH.required
def leave_game():
    """
    Leave game, flash status, redirect back to /home
    """
    api = API()
    gameid = request.args.get('gameid', None)
    if gameid is None:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    try:
        gameid = int(gameid)
    except ValueError:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    userid = session['userid']
    response = api.leave_game(userid, gameid)
    if response is api.ERR_LEAVE_GAME_NOT_IN:
        msg = "You are not registered in game %s." % (gameid,)
    elif response is api.ERR_NO_SUCH_OPEN_GAME:
        msg = "Invalid game ID."
    elif isinstance(response, APIError):
        msg = "An unknown error occurred."
    else:
        msg = "You have left game %s." % (gameid,)
    flash(msg)
    return redirect(url_for('home_page'))

@APP.route('/game', methods=['GET', 'POST'])
@AUTH.required
def game_page():
    """
    User's view of the specified game
    """
    gameid = request.args.get('gameid', None)
    if gameid is None:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    try:
        gameid = int(gameid)
    except ValueError:
        flash("Invalid game ID.")
        return redirect(url_for('home_page'))
    userid = session['userid']
        
    api = API()
    response = api.get_private_game(gameid, userid)
    if isinstance(response, APIError):
        if response is api.ERR_NO_SUCH_RUNNING_GAME:
            msg = "Invalid game ID."
        else:
            msg = "An unknown error occurred."
        flash(msg)
        return redirect(url_for('home_page'))
    
    form = action_form(is_check=response.current_options.can_check(),
        is_raise=response.current_options.is_raise,
        can_raise=response.current_options.can_raise(),
        min_raise=response.current_options.min_raise,
        max_raise=response.current_options.max_raise)
    if form.validate_on_submit():
        fold = form.fold.data
        passive = form.passive.data
        aggressive = form.aggressive.data
        total = form.total.data
        range_action = dtos.RangeBasedActionDetails(fold, passive, aggressive,
                                                    total)
        response = api.perform_action(gameid, userid, range_action)
        # why do validation twice...
        if isinstance(response, APIError):
            if response is api.ERR_INVALID_RAISE_TOTAL:
                msg = "Invalid raise total."
            elif response is api.ERR_INVALID_RANGES:
                msg = "Invalid ranges for that action."
            else:
                msg = "An unknown error occurred."
            flash(msg)
            return redirect(url_for('game_page', gameid=gameid))
        else:
            flash("Action performed!")
        return redirect(url_for('game_page', gameid=gameid))
    
    title = 'Game %d' % (gameid,)
    return render_template('game.html', title=title, form=form,
        game_details=response.game_details, history=response.history,
        current_options=response.current_options,
        is_me=(userid == response.game_details.current_player.user.userid))
