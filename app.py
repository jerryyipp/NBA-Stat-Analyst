from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # Import text for prepared statements

app = Flask(__name__)

# Configure the SQLAlchemy Database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nba_stats.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'MyKey'  # Change this for production
db = SQLAlchemy(app)

# Define the Player model
class Player(db.Model):
    player_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team_name = db.Column(db.String, db.ForeignKey('team.team_name'), nullable=False, index=True)
    position = db.Column(db.String(50), index=True)
    height = db.Column(db.Float)  # Store height as float (in inches)

    __table_args__ = (
        db.Index('ix_player_team_name', 'team_name'),  # Add explicit index for team_name
        db.Index('ix_player_position', 'position')    # Add explicit index for position
    )

# Define the Team model
class Team(db.Model):
    team_name = db.Column(db.String(50), primary_key=True)
    city = db.Column(db.String(20), nullable=False)
    conference = db.Column(db.String(20), nullable=False)

# Home route
@app.route('/')
def home():
    players = Player.query.all()  # Retrieve all players
    return render_template('index.html', players=players)

######################################################################
#                               PLAYERS                              #
######################################################################

# Players route with filtering using ORM and Prepared Statements
@app.route('/players', methods=['GET', 'POST'])
def players():
    # Get action parameter to determine if we are clearing filters
    action = request.args.get('action')

    # If action is "clear", reset the filters
    if action == 'clear':
        team_filter = ''
        position_filter = ''
        height_filter = ''
    else:
        # Get filter parameters from the request
        team_filter = request.args.get('team', '')
        position_filter = request.args.get('position', '')
        height_filter = request.args.get('height', '')

    # Using a prepared statement to filter players
    query = text(""" 
        SELECT * FROM player
        WHERE (:team_filter IS NULL OR team_name = :team_filter)
        AND (:position_filter IS NULL OR position = :position_filter)
        AND (:height_filter IS NULL OR height = :height_filter)
    """)
    result = db.session.execute(query, {
        'team_filter': team_filter if team_filter else None,
        'position_filter': position_filter if position_filter else None,
        'height_filter': float(height_filter) if height_filter else None
    })
    players = result.fetchall()

    # Get all distinct teams and positions for dropdowns
    teams = db.session.query(Team.team_name).all()
    positions = db.session.query(Player.position).distinct().all()

    return render_template(
        'players.html', 
        players=players, 
        teams=teams, 
        positions=positions, 
        team_filter=team_filter, 
        position_filter=position_filter, 
        height_filter=height_filter
    )

# Route to add a player using ORM
@app.route('/add', methods=['GET', 'POST'])
def add_player():
    teams = Team.query.all()

    if request.method == 'POST':
        name = request.form['name']
        team_name = request.form['team_name']
        position = request.form['position']
        height = request.form['height']

        # Convert height to float (in inches)
        try:
            height_in_inches = float(height)  # Expecting height in inches
        except ValueError:
            flash('Please enter a valid height in inches.')
            return redirect(url_for('add_player'))

        # Check if the team exists, if not assign "Free Agent"
        if not Team.query.filter_by(team_name=team_name).first():
            team_name = "Free Agent"

        new_player = Player(name=name, team_name=team_name, position=position, height=height_in_inches)
        db.session.add(new_player)
        db.session.commit()
        flash('Player added successfully!')
        return redirect(url_for('players'))

    return render_template('add_player.html', teams=teams)

# Route to edit a player using ORM
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)

    if request.method == 'POST':
        player.name = request.form['name']
        player.team_name = request.form['team_name']
        player.position = request.form['position']
        height = request.form['height']

        # Convert height to float (in inches)
        try:
            player.height = float(height)
        except ValueError:
            flash('Please enter a valid height in inches.')
            return redirect(url_for('edit_player', player_id=player_id))

        db.session.commit()
        flash('Player updated successfully!')
        return redirect(url_for('players'))

    return render_template('edit_player.html', player=player)

# Route to delete a player using ORM
@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully!')
    return redirect(url_for('players'))

######################################################################
#                            STATISTICS                              #
######################################################################

# Route for statistics using Prepared Statements
@app.route('/statistics', methods=['GET'])
def statistics():
    # Check for the action, default is to filter
    action = request.args.get('action')
    
    if action == 'clear':
        # Reset filters if "Clear Filters" is pressed
        team_filter = ''
        position_filter = ''
        height_filter = ''
    else:
        # Get filters if "Filter" button is pressed or no action specified
        team_filter = request.args.get('team', '')
        position_filter = request.args.get('position', '')
        height_filter = request.args.get('height', '')

    # Query distinct teams and positions for filter options
    teams = Team.query.order_by(Team.team_name).all()
    positions = db.session.query(Player.position).distinct().order_by(Player.position).all()
    positions = [pos[0] for pos in positions if pos[0]]  # Extract position values

    # Use Prepared Statement to filter players
    query = text(""" 
        SELECT * FROM player
        WHERE (:team_filter IS NULL OR team_name = :team_filter)
        AND (:position_filter IS NULL OR position = :position_filter)
        AND (:height_filter IS NULL OR height = :height_filter)
    """)
    result = db.session.execute(query, {
        'team_filter': team_filter if team_filter else None,
        'position_filter': position_filter if position_filter else None,
        'height_filter': float(height_filter) if height_filter else None
    })
    players = result.fetchall()

    # Calculate additional statistics
    num_players = len(players)
    num_teams = Team.query.count()
    average_height = db.session.query(db.func.avg(Player.height)).scalar()

    # Average Height by Team using a prepared statement
    avg_height_query = text(""" 
        SELECT team_name, AVG(height) AS avg_height
        FROM player
        GROUP BY team_name
    """)
    avg_height_result = db.session.execute(avg_height_query)
    average_height_by_team = avg_height_result.fetchall()

    # Position Breakdown
    position_breakdown = db.session.query(
        Player.position,
        db.func.count(Player.player_id).label('num_players')
    ).group_by(Player.position).all()

    # Render the template with filtered or cleared data
    return render_template(
        'statistics.html',
        teams=teams,
        positions=positions,
        players=players,
        num_players=num_players,
        num_teams=num_teams,
        average_height=average_height,
        average_height_by_team=average_height_by_team,
        position_breakdown=position_breakdown,
        team_filter=team_filter,
        position_filter=position_filter,
        height_filter=height_filter
    )


######################################################################
#                            END STATISTICS                          #
######################################################################

######################################################################
#                                 TEAMS                              #
######################################################################

@app.route('/teams', methods=['GET', 'POST'])
def teams():
    if request.method == 'POST':
        team_name = request.form['team_name']
        city = request.form['city']
        conference = request.form['conference']

        new_team = Team(team_name=team_name, city=city, conference=conference)
        db.session.add(new_team)
        db.session.commit()
        flash('Team added successfully!')
        return redirect(url_for('teams'))

    teams = Team.query.all()
    return render_template('teams.html', teams=teams)

@app.route('/edit_team/<string:team_name>', methods=['GET', 'POST'])
def edit_team(team_name):
    team = Team.query.get_or_404(team_name)

    if request.method == 'POST':
        team.city = request.form['city']
        team.conference = request.form['conference']
        db.session.commit()
        flash('Team updated successfully!')
        return redirect(url_for('teams'))

    return render_template('edit_team.html', team=team)

@app.route('/delete_team/<string:team_name>', methods=['POST'])
def delete_team(team_name):
    team = Team.query.get_or_404(team_name)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted successfully!')
    return redirect(url_for('teams'))

######################################################################
#                            END TEAMS                               #
######################################################################

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create all the tables if they don't exist
    app.run(debug=True)
