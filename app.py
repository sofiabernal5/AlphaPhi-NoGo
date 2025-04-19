from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import os
from werkzeug.utils import secure_filename
import tempfile
import numpy as np

app = Flask(__name__)
app.secret_key = 'Martha1872'  # Required for flashing messages

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

class Person:
    def __init__(self, last_name, first_name, sisterhood, character, generosity, innovation, bonus, total, senior=False):
        self.last_name = last_name
        self.first_name = first_name
        self.sisterhood = sisterhood
        self.character = character
        self.generosity = generosity
        self.innovation = innovation
        self.bonus = bonus
        self.total = total
        self.senior = senior
        
        # Initialize bonus allocation - now only one category will get bonus
        self.bonus_category = None
        
        # New fields to track bonus allocation
        self.sisterhood_with_bonus = sisterhood
        self.character_with_bonus = character
        self.generosity_with_bonus = generosity
        self.innovation_with_bonus = innovation

        # Track which thresholds the person is below
        self.below_thresholds = []
        
        # Track which thresholds the person is still below after bonus
        self.still_below_thresholds = []
        
    def allocate_bonus_points(self, thresholds):
        """Allocate all bonus points to the single category with the highest relative deficit"""
        # If this person is a senior, we don't need to allocate bonus points
        if self.senior:
            return
            
        if self.bonus <= 0:
            return
        
        # Calculate how many points each category is below its threshold
        deficits = {
            'sisterhood': max(0, thresholds['sisterhood'] - self.sisterhood),
            'character': max(0, thresholds['character'] - self.character),
            'generosity': max(0, thresholds['generosity'] - self.generosity),
            'innovation': max(0, thresholds['innovation'] - self.innovation)
        }
        
        # Track which thresholds the person is below
        if deficits['sisterhood'] > 0:
            self.below_thresholds.append('sisterhood')
        if deficits['character'] > 0:
            self.below_thresholds.append('character')
        if deficits['generosity'] > 0:
            self.below_thresholds.append('generosity')
        if deficits['innovation'] > 0:
            self.below_thresholds.append('innovation')
        
        # If no thresholds are below, don't allocate bonus
        if not self.below_thresholds:
            return
        
        # Normalize deficits by threshold to get relative deficits
        relative_deficits = {
            'sisterhood': deficits['sisterhood'] / thresholds['sisterhood'] if thresholds['sisterhood'] > 0 else 0,
            'character': deficits['character'] / thresholds['character'] if thresholds['character'] > 0 else 0,
            'generosity': deficits['generosity'] / thresholds['generosity'] if thresholds['generosity'] > 0 else 0,
            'innovation': deficits['innovation'] / thresholds['innovation'] if thresholds['innovation'] > 0 else 0
        }
            
        # Find category with highest relative deficit
        max_deficit_category = max(relative_deficits, key=lambda k: relative_deficits[k])
        
        # If no deficits, don't allocate bonus
        if relative_deficits[max_deficit_category] <= 0:
            return
            
        # Allocate all bonus points to this single category
        self.bonus_category = max_deficit_category
        
        # Update the with_bonus fields based on allocation
        if max_deficit_category == 'sisterhood':
            self.sisterhood_with_bonus = self.sisterhood + self.bonus
        elif max_deficit_category == 'character':
            self.character_with_bonus = self.character + self.bonus
        elif max_deficit_category == 'generosity':
            self.generosity_with_bonus = self.generosity + self.bonus
        elif max_deficit_category == 'innovation':
            self.innovation_with_bonus = self.innovation + self.bonus
        
        # Calculate which thresholds the person is still below after bonus allocation
        if self.sisterhood_with_bonus < thresholds['sisterhood']:
            self.still_below_thresholds.append('sisterhood')
        if self.character_with_bonus < thresholds['character']:
            self.still_below_thresholds.append('character')
        if self.generosity_with_bonus < thresholds['generosity']:
            self.still_below_thresholds.append('generosity')
        if self.innovation_with_bonus < thresholds['innovation']:
            self.still_below_thresholds.append('innovation')

    def get_formatted_name(self):
        """Create a properly formatted name string for display"""
        if self.first_name and self.last_name:
            return f"{self.last_name}, {self.first_name}"
        elif self.last_name:
            return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return "Unknown"

def check_sisterhood(people, threshold):
    below_threshold = []
    for person in people:
        # Skip seniors
        if person.senior:
            continue
            
        if person.sisterhood_with_bonus < threshold:  # Check after bonus
            missing_sis = threshold - person.sisterhood
            
            # Get bonus allocated to sisterhood
            bonus_used = person.bonus if person.bonus_category == 'sisterhood' else 0
            new_total = person.sisterhood_with_bonus
            
            # Add the person to the results if they're below threshold after bonus
            below_threshold.append({
                'name': person.get_formatted_name(),
                'current': person.sisterhood,
                'new_total': new_total,
                'missing': max(0, threshold - new_total),
                'bonus_used': bonus_used
            })
    return below_threshold

def check_character(people, threshold):
    below_threshold = []
    for person in people:
        # Skip seniors
        if person.senior:
            continue
            
        if person.character_with_bonus < threshold:  # Check after bonus
            missing_char = threshold - person.character
            
            # Get bonus allocated to character
            bonus_used = person.bonus if person.bonus_category == 'character' else 0
            new_total = person.character_with_bonus
            
            # Add the person to the results if they're below threshold after bonus
            below_threshold.append({
                'name': person.get_formatted_name(),
                'current': person.character,
                'new_total': new_total,
                'missing': max(0, threshold - new_total),
                'bonus_used': bonus_used
            })
    return below_threshold

def check_generosity(people, threshold):
    below_threshold = []
    for person in people:
        # Skip seniors
        if person.senior:
            continue
            
        if person.generosity_with_bonus < threshold:  # Check after bonus
            missing_gen = threshold - person.generosity
            
            # Get bonus allocated to generosity
            bonus_used = person.bonus if person.bonus_category == 'generosity' else 0
            new_total = person.generosity_with_bonus
            
            # Add the person to the results if they're below threshold after bonus
            below_threshold.append({
                'name': person.get_formatted_name(),
                'current': person.generosity,
                'new_total': new_total,
                'missing': max(0, threshold - new_total),
                'bonus_used': bonus_used
            })
    return below_threshold

def check_innovation(people, threshold):
    below_threshold = []
    for person in people:
        # Skip seniors
        if person.senior:
            continue
            
        if person.innovation_with_bonus < threshold:  # Check after bonus
            missing_inno = threshold - person.innovation
            
            # Get bonus allocated to innovation
            bonus_used = person.bonus if person.bonus_category == 'innovation' else 0
            new_total = person.innovation_with_bonus
            
            # Add the person to the results if they're below threshold after bonus
            below_threshold.append({
                'name': person.get_formatted_name(),
                'current': person.innovation,
                'new_total': new_total,
                'missing': max(0, threshold - new_total),
                'bonus_used': bonus_used
            })
    return below_threshold

def check_potential_seniors(people):
    """Identify members who have a zero in at least one category but aren't marked as seniors"""
    potential_seniors = []
    for person in people:
        # Skip those already marked as seniors
        if person.senior:
            continue
            
        if (person.sisterhood == 0 or person.character == 0 or 
            person.generosity == 0 or person.innovation == 0):
            # Create a proper name string
            potential_seniors.append(f"{person.first_name} {person.last_name}")
    return potential_seniors

def create_unique_member_list(people, thresholds):
    """Create a list of members who are below at least one threshold (before or after bonus)"""
    unique_members = []
    for person in people:
        # Skip seniors
        if person.senior:
            continue
            
        # Check if person is below threshold in ANY category (using original scores)
        if (person.sisterhood < thresholds['sisterhood'] or 
            person.character < thresholds['character'] or 
            person.generosity < thresholds['generosity'] or 
            person.innovation < thresholds['innovation']):
            
            # Add all categories where they're below threshold
            categories_below = []
            
            # Check Sisterhood
            if person.sisterhood < thresholds['sisterhood']:
                categories_below.append({
                    'name': 'Sisterhood',
                    'current': person.sisterhood,
                    'with_bonus': person.sisterhood_with_bonus,
                    'threshold': thresholds['sisterhood'],
                    'missing': max(0, thresholds['sisterhood'] - person.sisterhood_with_bonus),
                    'has_bonus': person.bonus_category == 'sisterhood'
                })
                
            # Check Character
            if person.character < thresholds['character']:
                categories_below.append({
                    'name': 'Character',
                    'current': person.character,
                    'with_bonus': person.character_with_bonus,
                    'threshold': thresholds['character'],
                    'missing': max(0, thresholds['character'] - person.character_with_bonus),
                    'has_bonus': person.bonus_category == 'character'
                })
                
            # Check Generosity
            if person.generosity < thresholds['generosity']:
                categories_below.append({
                    'name': 'Generosity',
                    'current': person.generosity,
                    'with_bonus': person.generosity_with_bonus,
                    'threshold': thresholds['generosity'],
                    'missing': max(0, thresholds['generosity'] - person.generosity_with_bonus),
                    'has_bonus': person.bonus_category == 'generosity'
                })
                
            # Check Innovation
            if person.innovation < thresholds['innovation']:
                categories_below.append({
                    'name': 'Innovation',
                    'current': person.innovation,
                    'with_bonus': person.innovation_with_bonus,
                    'threshold': thresholds['innovation'],
                    'missing': max(0, thresholds['innovation'] - person.innovation_with_bonus),
                    'has_bonus': person.bonus_category == 'innovation'
                })
                
            # Only add to the unique list if they have at least one category still below threshold
            if any(cat['missing'] > 0 for cat in categories_below):
                unique_members.append({
                    'name': person.get_formatted_name(),
                    'categories': categories_below,
                    'bonus': person.bonus,
                    'bonus_category': person.bonus_category
                })
            
    return unique_members

def create_full_member_list(people, thresholds):
    """Create a list of all members with their status"""
    full_members = []
    for person in people:
        # For all members including seniors
        full_members.append({
            'name': person.get_formatted_name(),
            'senior': person.senior,
            'sisterhood': person.sisterhood,
            'sisterhood_with_bonus': person.sisterhood_with_bonus,
            'sisterhood_threshold': thresholds['sisterhood'],
            'sisterhood_below': person.sisterhood < thresholds['sisterhood'],
            'character': person.character,
            'character_with_bonus': person.character_with_bonus,
            'character_threshold': thresholds['character'],
            'character_below': person.character < thresholds['character'],
            'generosity': person.generosity,
            'generosity_with_bonus': person.generosity_with_bonus,
            'generosity_threshold': thresholds['generosity'],
            'generosity_below': person.generosity < thresholds['generosity'],
            'innovation': person.innovation,
            'innovation_with_bonus': person.innovation_with_bonus,
            'innovation_threshold': thresholds['innovation'],
            'innovation_below': person.innovation < thresholds['innovation'],
            'bonus': person.bonus,
            'bonus_category': person.bonus_category,
            'total': person.total
        })
    return full_members

def load_seniors_list(file_path, senior_first_name_idx=0, senior_last_name_idx=1):
    """Load seniors list from CSV file"""
    seniors = []
    
    try:
        # Check file extension
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path, header=None)
        else:  # Excel file
            df = pd.read_excel(file_path, header=None)
        
        for idx, row in df.iterrows():
            # Extract names from the specified columns
            if senior_first_name_idx < len(row) and senior_last_name_idx < len(row):
                first_name = str(row.iloc[senior_first_name_idx]) if pd.notna(row.iloc[senior_first_name_idx]) else ''
                last_name = str(row.iloc[senior_last_name_idx]) if pd.notna(row.iloc[senior_last_name_idx]) else ''
                
                # Skip rows with empty names
                if (first_name == '' or first_name == 'nan') and (last_name == '' or last_name == 'nan'):
                    continue
                
                # Trim whitespace and convert to lowercase for better matching
                first_name = first_name.strip().lower()
                last_name = last_name.strip().lower()
                
                # Add to seniors list
                seniors.append({
                    'first_name': first_name,
                    'last_name': last_name
                })
    
    except Exception as e:
        print(f"Error loading seniors list: {str(e)}")
    
    return seniors

def is_senior(person, seniors_list):
    """Check if a person is in the seniors list"""
    person_first = person.first_name.strip().lower()
    person_last = person.last_name.strip().lower()
    
    for senior in seniors_list:
        if (person_first == senior['first_name'] and person_last == senior['last_name']):
            return True
    return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if file part exists
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        # Get seniors file if provided
        seniors_file = request.files.get('seniors_file')
        seniors_list = []
        
        if seniors_file and allowed_file(seniors_file.filename):
            seniors_filename = secure_filename(seniors_file.filename)
            seniors_file_path = os.path.join(app.config['UPLOAD_FOLDER'], seniors_filename)
            seniors_file.save(seniors_file_path)
            
            # Get senior column indexes
            senior_first_name_idx = int(request.form.get('senior_first_name_idx', 0))
            senior_last_name_idx = int(request.form.get('senior_last_name_idx', 1))
            
            # Load seniors list
            seniors_list = load_seniors_list(seniors_file_path, senior_first_name_idx, senior_last_name_idx)
            flash(f'Loaded {len(seniors_list)} seniors from file')
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Get thresholds from form
            sisterhood_threshold = int(request.form.get('sisterhood_threshold', 30))
            character_threshold = int(request.form.get('character_threshold', 23))
            generosity_threshold = int(request.form.get('generosity_threshold', 10))
            innovation_threshold = int(request.form.get('innovation_threshold', 10))
            
            # Create thresholds dictionary
            thresholds = {
                'sisterhood': sisterhood_threshold,
                'character': character_threshold,
                'generosity': generosity_threshold,
                'innovation': innovation_threshold
            }
            
            # Get column indexes from form (for CSV files)
            last_name_idx = int(request.form.get('last_name_idx', 0))
            first_name_idx = int(request.form.get('first_name_idx', 1))
            sisterhood_idx = int(request.form.get('sisterhood_idx', 2))
            character_idx = int(request.form.get('character_idx', 3))
            generosity_idx = int(request.form.get('generosity_idx', 4))
            innovation_idx = int(request.form.get('innovation_idx', 5))
            bonus_idx = int(request.form.get('bonus_idx', 6))
            total_idx = int(request.form.get('total_idx', 7))
            
            try:
                # Check if it's a CSV file
                if filename.lower().endswith('.csv'):
                    # Read CSV file, skip first row as requested
                    df = pd.read_csv(file_path, header=None, skiprows=1)
                    
                    # Process data
                    people = []
                    seniors_count = 0
                    for idx, row in df.iterrows():
                        # For CSV files, use column indexes instead of names
                        if len(row) > max(last_name_idx, first_name_idx):
                            last_name = str(row.iloc[last_name_idx]) if pd.notna(row.iloc[last_name_idx]) else ''
                            first_name = str(row.iloc[first_name_idx]) if pd.notna(row.iloc[first_name_idx]) else ''
                            
                            # Skip rows with empty names
                            if (last_name == '' or last_name == 'nan') and (first_name == '' or first_name == 'nan'):
                                continue
                            
                            # Handle numeric columns
                            sisterhood = int(float(row.iloc[sisterhood_idx])) if sisterhood_idx < len(row) and pd.notna(row.iloc[sisterhood_idx]) else 0
                            character = int(float(row.iloc[character_idx])) if character_idx < len(row) and pd.notna(row.iloc[character_idx]) else 0
                            generosity = int(float(row.iloc[generosity_idx])) if generosity_idx < len(row) and pd.notna(row.iloc[generosity_idx]) else 0
                            innovation = int(float(row.iloc[innovation_idx])) if innovation_idx < len(row) and pd.notna(row.iloc[innovation_idx]) else 0
                            bonus = int(float(row.iloc[bonus_idx])) if bonus_idx < len(row) and pd.notna(row.iloc[bonus_idx]) else 0
                            total = int(float(row.iloc[total_idx])) if total_idx < len(row) and pd.notna(row.iloc[total_idx]) else 0
                            
                            # Calculate total if not provided
                            if total == 0:
                                total = sisterhood + character + generosity + innovation + bonus
                            
                            # Create person object
                            person = Person(
                                last_name=last_name,
                                first_name=first_name,
                                sisterhood=sisterhood,
                                character=character,
                                generosity=generosity,
                                innovation=innovation,
                                bonus=bonus,
                                total=total
                            )
                            
                            # Check if this person is a senior
                            person.senior = is_senior(person, seniors_list)
                            if person.senior:
                                seniors_count += 1
                            
                            # Allocate bonus points based on needs
                            person.allocate_bonus_points(thresholds)
                            
                            people.append(person)
                else:
                    # Handle Excel files
                    df = pd.read_excel(file_path, header=None, skiprows=1)
                    
                    # Process data (same as CSV but using column indexes)
                    people = []
                    seniors_count = 0
                    for idx, row in df.iterrows():
                        # For Excel files, use column indexes
                        if len(row) > max(last_name_idx, first_name_idx):
                            last_name = str(row.iloc[last_name_idx]) if pd.notna(row.iloc[last_name_idx]) else ''
                            first_name = str(row.iloc[first_name_idx]) if pd.notna(row.iloc[first_name_idx]) else ''
                            
                            # Skip rows with empty names
                            if (last_name == '' or last_name == 'nan') and (first_name == '' or first_name == 'nan'):
                                continue
                            
                            # Handle numeric columns
                            sisterhood = int(float(row.iloc[sisterhood_idx])) if sisterhood_idx < len(row) and pd.notna(row.iloc[sisterhood_idx]) else 0
                            character = int(float(row.iloc[character_idx])) if character_idx < len(row) and pd.notna(row.iloc[character_idx]) else 0
                            generosity = int(float(row.iloc[generosity_idx])) if generosity_idx < len(row) and pd.notna(row.iloc[generosity_idx]) else 0
                            innovation = int(float(row.iloc[innovation_idx])) if innovation_idx < len(row) and pd.notna(row.iloc[innovation_idx]) else 0
                            bonus = int(float(row.iloc[bonus_idx])) if bonus_idx < len(row) and pd.notna(row.iloc[bonus_idx]) else 0
                            total = int(float(row.iloc[total_idx])) if total_idx < len(row) and pd.notna(row.iloc[total_idx]) else 0
                            
                            # Calculate total if not provided
                            if total == 0:
                                total = sisterhood + character + generosity + innovation + bonus
                            
                            # Create person object
                            person = Person(
                                last_name=last_name,
                                first_name=first_name,
                                sisterhood=sisterhood,
                                character=character,
                                generosity=generosity,
                                innovation=innovation,
                                bonus=bonus,
                                total=total
                            )
                            
                            # Check if this person is a senior
                            person.senior = is_senior(person, seniors_list)
                            if person.senior:
                                seniors_count += 1
                            
                            # Allocate bonus points based on needs
                            person.allocate_bonus_points(thresholds)
                            
                            people.append(person)
                
                # Flash message about seniors found
                if seniors_count > 0:
                    flash(f'{seniors_count} members identified as seniors and excluded from requirements')
                
                # Check thresholds
                sisterhood_results = check_sisterhood(people, sisterhood_threshold)
                character_results = check_character(people, character_threshold)
                generosity_results = check_generosity(people, generosity_threshold)
                innovation_results = check_innovation(people, innovation_threshold)
                
                # Create the unique member list
                unique_members = create_unique_member_list(people, thresholds)
                
                # Create the full member list (all members)
                full_member_list = create_full_member_list(people, thresholds)
                
                # Check for potential seniors
                potential_seniors = check_potential_seniors(people)
                
                # Get list of confirmed seniors for display
                confirmed_seniors = []
                for person in people:
                    if person.senior:
                        confirmed_seniors.append(person.get_formatted_name())
                
                # Display column indices used
                column_indices_used = {
                    'Last Name': last_name_idx,
                    'First Name': first_name_idx,
                    'Sisterhood': sisterhood_idx,
                    'Character': character_idx,
                    'Generosity': generosity_idx,
                    'Innovation': innovation_idx,
                    'Bonus': bonus_idx,
                    'Total': total_idx
                }
                
                return render_template('results_with_bonus.html',
                                      sisterhood_results=sisterhood_results,
                                      character_results=character_results,
                                      generosity_results=generosity_results,
                                      innovation_results=innovation_results,
                                      potential_seniors=potential_seniors,
                                      confirmed_seniors=confirmed_seniors,
                                      full_member_list=full_member_list,
                                      unique_members=unique_members,
                                      sisterhood_threshold=sisterhood_threshold,
                                      character_threshold=character_threshold,
                                      generosity_threshold=generosity_threshold,
                                      innovation_threshold=innovation_threshold,
                                      column_mappings=column_indices_used,
                                      total_members=len(people))
            
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                flash(f'Error processing file: {str(e)}')
                flash(f'Details: {error_details}')
                return redirect(request.url)
        else:
            flash('Allowed file types are .csv, .xlsx and .xls')
            return redirect(request.url)
            
    return render_template('index_csv_seniors.html')

@app.route('/export_results', methods=['POST'])
def export_results():
    # Get data from the form
    sisterhood_data = request.form.get('sisterhood_data', '[]')
    character_data = request.form.get('character_data', '[]')
    generosity_data = request.form.get('generosity_data', '[]')
    innovation_data = request.form.get('innovation_data', '[]')
    potential_seniors = request.form.get('potential_seniors', '[]')
    confirmed_seniors = request.form.get('confirmed_seniors', '[]')
    unique_members_data = request.form.get('unique_members_data', '[]')
    full_member_list_data = request.form.get('full_member_list', '[]')
    
    # Create DataFrame for each category
    sisterhood_df = pd.DataFrame(eval(sisterhood_data)) if sisterhood_data != '[]' else pd.DataFrame()
    character_df = pd.DataFrame(eval(character_data)) if character_data != '[]' else pd.DataFrame()
    generosity_df = pd.DataFrame(eval(generosity_data)) if generosity_data != '[]' else pd.DataFrame()
    innovation_df = pd.DataFrame(eval(innovation_data)) if innovation_data != '[]' else pd.DataFrame()
    potential_seniors_df = pd.DataFrame({'Name': eval(potential_seniors)}) if potential_seniors != '[]' else pd.DataFrame()
    confirmed_seniors_df = pd.DataFrame({'Name': eval(confirmed_seniors)}) if confirmed_seniors != '[]' else pd.DataFrame()
    
    # Create a unique members DataFrame if data is available
    unique_members_df = pd.DataFrame()
    if unique_members_data != '[]':
        members = eval(unique_members_data)
        data = []
        for member in members:
            categories = ", ".join([c['name'] for c in member['categories']])
            bonus_category = member['bonus_category'].capitalize() if member['bonus_category'] else 'None'
            data.append({
                'Name': member['name'],
                'Categories Below Threshold': categories,
                'Bonus Points': member['bonus'],
                'Bonus Allocated To': bonus_category
            })
        unique_members_df = pd.DataFrame(data)
    
    # Create a full member list DataFrame if data is available
    full_member_df = pd.DataFrame()
    if full_member_list_data != '[]':
        try:
            members = eval(full_member_list_data)
            data = []
            for member in members:
                data.append({
                    'Name': member['name'],
                    'Senior': 'Yes' if member['senior'] else 'No',
                    'Sisterhood': member['sisterhood'],
                    'Sisterhood Threshold': member['sisterhood_threshold'],
                    'Character': member['character'],
                    'Character Threshold': member['character_threshold'],
                    'Generosity': member['generosity'],
                    'Generosity Threshold': member['generosity_threshold'],
                    'Innovation': member['innovation'],
                    'Innovation Threshold': member['innovation_threshold'],
                    'Bonus Points': member['bonus'],
                    'Bonus Category': member['bonus_category'].capitalize() if member['bonus_category'] else 'None',
                    'Total': member['total']
                })
            full_member_df = pd.DataFrame(data)
        except Exception as e:
            print(f"Error creating full member DataFrame: {str(e)}")
    
            # Create a temporary file to store the Excel
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp:
        # Create ExcelWriter object
        writer = pd.ExcelWriter(temp.name, engine='xlsxwriter')
        
        # Write full member list to the first sheet
        if not full_member_df.empty:
            full_member_df.to_excel(writer, sheet_name='All Members', index=False)
            
        # Write unique members to the second sheet
        if not unique_members_df.empty:
            unique_members_df.to_excel(writer, sheet_name='Members Below Threshold', index=False)
            
        # Write each DataFrame to a different sheet
        if not sisterhood_df.empty:
            sisterhood_df.to_excel(writer, sheet_name='Sisterhood', index=False)
        if not character_df.empty:
            character_df.to_excel(writer, sheet_name='Character', index=False)
        if not generosity_df.empty:
            generosity_df.to_excel(writer, sheet_name='Generosity', index=False)
        if not innovation_df.empty:
            innovation_df.to_excel(writer, sheet_name='Innovation', index=False)
        if not potential_seniors_df.empty:
            potential_seniors_df.to_excel(writer, sheet_name='Potential Seniors', index=False)
        if not confirmed_seniors_df.empty:
            confirmed_seniors_df.to_excel(writer, sheet_name='Confirmed Seniors', index=False)
            
        # Save the Excel file
        writer.close()
        
        # Return the file as a download
        return send_file(temp.name, 
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        download_name='requirements_results.xlsx',
                        as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)