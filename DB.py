import psycopg2

connection = None

try:
    # 1. Connect to the database
    connection = psycopg2.connect(
        user="postgres",
        password="password",
        host="localhost",
        port="5432",
        database="recruit_ai"
    )

    # 2. Create cursor
    cursor = connection.cursor()

    # 3. Create candidate table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS candidate (
        candidate_id SERIAL PRIMARY KEY,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        mobile_no VARCHAR(20),
        email_id VARCHAR(255),
        nationality VARCHAR(100),
        highest_qualification TEXT,
        total_experience_years FLOAT,
        projects_worked INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_project_table_query = """
    CREATE TABLE IF NOT EXISTS project (
        project_id SERIAL PRIMARY KEY,
        candidate_id INTEGER REFERENCES candidate(candidate_id) ON DELETE CASCADE,
        project_name VARCHAR(255),  -- Increased length
        project_description TEXT,   -- Changed to TEXT for longer descriptions
        project_duration VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_skills_table_query = """
    CREATE TABLE IF NOT EXISTS candidate_skills (
        skill_id SERIAL PRIMARY KEY,
        candidate_id INTEGER REFERENCES candidate(candidate_id) ON DELETE CASCADE,
        skill_name VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(candidate_id, skill_name)
    );
    """

    # Execute table creation queries
    cursor.execute(create_table_query)
    cursor.execute(create_project_table_query)
    cursor.execute(create_skills_table_query)
    connection.commit()

    def candidate_exsits(response):
        number=str(response.mobile_no)
        query="""SELECT candidate_id FROM candidate
        WHERE mobile_no = %s
        """
        cursor.execute(query,(number,))
        result = cursor.fetchone()

        if result!= None:
            return True
        else:
            return False
        
    
    
    def insert_candidate(response):
        """Insert candidate and return candidate_id"""
        query = """INSERT INTO candidate (
            first_name,
            last_name,
            mobile_no,
            email_id,
            nationality,
            highest_qualification,
            total_experience_years,
            projects_worked
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING candidate_id;"""  
        
        values = (
            response.first_name,      
            response.last_name,
            response.mobile_no,
            response.email_id,
            response.nationality,
            response.highest_qualification,
            response.total_experience_years,
            response.projects_worked
        )
        
        cursor.execute(query, values)
        candidate_id = cursor.fetchone()[0]  
        connection.commit()
        
        print(f"Candidate inserted with ID: {candidate_id}")
        return candidate_id
    
    def insert_projects(candidate_id, project_names, project_descriptions):
        """Insert multiple projects for a candidate"""
        project_duration = None  
        
        project_query = """
        INSERT INTO project (candidate_id, project_name, project_description, project_duration)
        VALUES (%s, %s, %s, %s)
        """
        
        for project_name, project_desc in zip(project_names, project_descriptions):
            cursor.execute(project_query, (candidate_id, project_name, project_desc, project_duration))
        
        connection.commit()
        print(f"Inserted {len(project_names)} projects for candidate {candidate_id}")
    
    def insert_skills(candidate_id, skills_list):
        """Insert multiple skills for a candidate"""
        skill_query = """
        INSERT INTO candidate_skills (candidate_id, skill_name)
        VALUES (%s, %s)
        ON CONFLICT (candidate_id, skill_name) DO NOTHING  -- Avoid duplicates
        """
        
        for skill in skills_list:
            cursor.execute(skill_query, (candidate_id, skill))
        
        connection.commit()
        print(f"Inserted {len(skills_list)} skills for candidate {candidate_id}")



except (Exception, psycopg2.Error) as error:
    print("Error while connecting to PostgreSQL", error)
    if connection:
        connection.rollback()
