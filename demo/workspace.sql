BEGIN TRANSACTION;
CREATE TABLE candidate_skills (
                candidate_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,

                evidence_status TEXT NOT NULL
                    CHECK (
                        evidence_status IN (
                            'evidenced',
                            'developing',
                            'self_reported'
                        )
                    ),

                evidence_note TEXT,

                PRIMARY KEY (candidate_id, skill_id),

                FOREIGN KEY (candidate_id)
                    REFERENCES candidates(candidate_id),

                FOREIGN KEY (skill_id)
                    REFERENCES skills(skill_id),

                CHECK (
                    evidence_status != 'evidenced'
                    OR (
                        evidence_note IS NOT NULL
                        AND length(
                            trim(
                                evidence_note,
                                char(9) || char(10) || char(13) || ' '
                            )
                        ) > 0
                    )
                )
            );
INSERT INTO "candidate_skills" VALUES(1,1,'evidenced','Coursework Project');
INSERT INTO "candidate_skills" VALUES(1,2,'evidenced','Coursework Project');
INSERT INTO "candidate_skills" VALUES(1,18,'developing',NULL);
INSERT INTO "candidate_skills" VALUES(1,39,'developing',NULL);
INSERT INTO "candidate_skills" VALUES(1,47,'self_reported',NULL);
INSERT INTO "candidate_skills" VALUES(1,38,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(1,42,'developing',NULL);
INSERT INTO "candidate_skills" VALUES(2,57,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(2,3,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(2,56,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(2,55,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(2,53,'evidenced','project');
INSERT INTO "candidate_skills" VALUES(2,43,'evidenced','project');
CREATE TABLE candidates (
                candidate_id INTEGER PRIMARY KEY,
                display_name TEXT
            );
INSERT INTO "candidates" VALUES(1,'bhanu');
INSERT INTO "candidates" VALUES(2,'test');
CREATE TABLE completion_alias_state(alias TEXT PRIMARY KEY,skill_id INTEGER NOT NULL REFERENCES skills(skill_id),active INTEGER NOT NULL CHECK(active IN(0,1)),reason TEXT NOT NULL,changed_at TEXT NOT NULL);
INSERT INTO "completion_alias_state" VALUES('java',52,1,'nothing','2026-10-21T17:08:10.658737+00:00');
INSERT INTO "completion_alias_state" VALUES('agents',54,1,'none before','2026-10-22T15:51:37.984079+00:00');
CREATE TABLE completion_esco(skill_id INTEGER PRIMARY KEY REFERENCES skills(skill_id),uri TEXT NOT NULL,preferred_label TEXT NOT NULL,classification_version TEXT NOT NULL,language TEXT NOT NULL,source_url TEXT NOT NULL,file_sha256 TEXT NOT NULL,source_row_json TEXT NOT NULL,relation TEXT NOT NULL CHECK(relation IN('exact','broader','related')),reason TEXT NOT NULL,mapped_at TEXT NOT NULL);
CREATE TABLE completion_events(event_id INTEGER PRIMARY KEY,event_type TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL);
INSERT INTO "completion_events" VALUES(1,'alias_change','{"active": true, "alias": "java", "reason": "not included earlier", "skill_id": 52}','2026-10-21T00:18:32.791061+00:00');
INSERT INTO "completion_events" VALUES(2,'alias_change','{"active": true, "alias": "java", "reason": "not included earlier", "skill_id": 52}','2026-10-21T00:18:38.671785+00:00');
INSERT INTO "completion_events" VALUES(3,'alias_change','{"active": true, "alias": "java", "reason": "nothing", "skill_id": 52}','2026-10-21T17:08:10.675848+00:00');
INSERT INTO "completion_events" VALUES(4,'alias_change','{"active": true, "alias": "agents", "reason": "none before", "skill_id": 54}','2026-10-22T15:51:37.984079+00:00');
CREATE TABLE completion_language_reviews(job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,source_hash TEXT NOT NULL,language TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN('required','desirable','not_required','uncertain')),reason TEXT NOT NULL,automatic_json TEXT NOT NULL,reviewed_at TEXT NOT NULL,PRIMARY KEY(job_id,source_hash,language,start_offset,end_offset));
CREATE TABLE jf_batch_events(event_id INTEGER PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE jf_batch_language(job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,source_hash TEXT NOT NULL,language TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('required','desirable','not_required','uncertain')),note TEXT NOT NULL,automatic_at_review TEXT NOT NULL,changed_at TEXT NOT NULL,PRIMARY KEY(job_id,source_hash,language,start_offset,end_offset));
CREATE TABLE jobfit_revisions(revision_id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL,saved_at TEXT NOT NULL,record_json TEXT NOT NULL,metadata_json TEXT NOT NULL);
INSERT INTO "jobfit_revisions" VALUES(1,15,'2026-10-20T21:50:52.114840+00:00','{"job_id": 15, "title": "sep. fict test 2", "description_text": "Python and SQL are required.", "source_description": "fict 2", "source_url": null, "date_added": "2026-10-20", "application_status": "Not applied"}','{"job_id": 15, "company": "", "location": "", "work_type": "", "source_language": ""}');
INSERT INTO "jobfit_revisions" VALUES(2,17,'2026-10-20T22:01:32.462665+00:00','{"job_id": 17, "title": "fict listing 4", "description_text": "Python is required. \nPython is desirable.", "source_description": "list 4", "source_url": null, "date_added": "2026-10-20", "application_status": "Not applied"}','{"job_id": 17, "company": "", "location": "", "work_type": "", "source_language": ""}');
INSERT INTO "jobfit_revisions" VALUES(3,18,'2026-10-20T22:03:42.321693+00:00','{"job_id": 18, "title": "fictional list 5", "description_text": "Python is desirable. Rust is required.", "source_description": "list 5", "source_url": null, "date_added": "2026-10-20", "application_status": "Not applied"}','{"job_id": 18, "company": "amr", "location": "berlin", "work_type": "internship", "source_language": "english"}');
INSERT INTO "jobfit_revisions" VALUES(4,20,'2026-10-20T22:13:05.369912+00:00','{"job_id": 20, "title": "state change", "description_text": "python is required", "source_description": "reg.", "source_url": null, "date_added": "2026-10-20", "application_status": "Not applied"}','{"job_id": 20, "company": "", "location": "", "work_type": "", "source_language": ""}');
INSERT INTO "jobfit_revisions" VALUES(5,21,'2026-10-21T17:00:13.910549+00:00','{"job_id": 21, "title": "java developer", "description_text": "i need a guy experienced in java and javascript", "source_description": "developer .co", "source_url": null, "date_added": "2026-10-21", "application_status": "Not applied"}','{"job_id": 21, "company": "", "location": "", "work_type": "", "source_language": ""}');
INSERT INTO "jobfit_revisions" VALUES(6,19,'2026-10-22T17:29:59.416471+00:00','{"job_id": 19, "title": "speak german bro", "description_text": "German B2 is required. \nEnglish is desirable.", "source_description": "germany ", "source_url": null, "date_added": "2026-10-20", "application_status": "Not applied"}','{"job_id": 19, "company": "swiss-german-austria", "location": "salzburg", "work_type": "permanent", "source_language": "english"}');
INSERT INTO "jobfit_revisions" VALUES(7,8,'2026-10-22T17:31:42.772353+00:00','{"job_id": 8, "title": "Fictional demo \u2014 Praktikum Datenwissenschaft", "description_text": "Entwickle Modelle f\u00fcr maschinelles Lernen mit Python.\nWerte Experimente aus und dokumentiere die Ergebnisse.", "source_description": "created manually synthetic", "source_url": null, "date_added": "2026-10-17", "application_status": "Not applied"}','{"job_id": 8, "company": "praktikum", "location": "berlin", "work_type": "internship", "source_language": "german"}');
INSERT INTO "jobfit_revisions" VALUES(8,9,'2026-10-22T17:32:45.857253+00:00','{"job_id": 9, "title": "fict-helloo", "description_text": "hi how are you\ni need freelancer with python experience\ni also need sql and aws and powerbi experienced guy", "source_description": "trust me bro", "source_url": null, "date_added": "2026-10-17", "application_status": "Not applied"}','{"job_id": 9, "company": "koo", "location": "erlangen", "work_type": "werk-student", "source_language": "english"}');
CREATE TABLE jobfit_user_concepts(skill_id INTEGER PRIMARY KEY REFERENCES skills(skill_id),created_at TEXT NOT NULL,aliases_json TEXT NOT NULL,origin TEXT NOT NULL);
INSERT INTO "jobfit_user_concepts" VALUES(52,'2026-10-21T00:16:35.632689+00:00','["java"]','explicit_user_entry');
INSERT INTO "jobfit_user_concepts" VALUES(53,'2026-10-21T00:19:29.851629+00:00','["javascript", "java script", "java-script"]','explicit_user_entry');
INSERT INTO "jobfit_user_concepts" VALUES(54,'2026-10-22T15:48:44.424468+00:00','["agentic ai"]','explicit_user_entry');
INSERT INTO "jobfit_user_concepts" VALUES(55,'2026-10-22T15:49:01.369573+00:00','["prompt engineering"]','explicit_user_entry');
INSERT INTO "jobfit_user_concepts" VALUES(56,'2026-10-22T15:50:06.423916+00:00','["hugging face"]','explicit_user_entry');
INSERT INTO "jobfit_user_concepts" VALUES(57,'2026-10-22T15:50:14.101829+00:00','["transformers"]','explicit_user_entry');
CREATE TABLE jobs (
                job_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description_text TEXT NOT NULL,
                source_description TEXT NOT NULL,
                source_url TEXT,
                date_added TEXT NOT NULL DEFAULT CURRENT_DATE,
                application_status TEXT NOT NULL DEFAULT 'Not applied'
            );
INSERT INTO "jobs" VALUES(1,'Integration demo','Python is required; SQL is desirable.
No Docker experience is required.','Fictional demonstration',NULL,'2026-10-14','Considering');
INSERT INTO "jobs" VALUES(2,'Integration demo 2','Python is required; Structured Query Language is desirable.
No amazon web services experience is required.','Fictional demonstration 2',NULL,'2026-10-14','Considering');
INSERT INTO "jobs" VALUES(4,'Integration Test 3','Aws is required. Power Bi is needed. Excel and sql are plus.','job 3',NULL,'2026-10-15','Considering');
INSERT INTO "jobs" VALUES(5,'Job fict test','Python is required.
Deutsch B2 ist erforderlich.
Fluent English is desirable.','created',NULL,'2026-10-16','Considering');
INSERT INTO "jobs" VALUES(6,'job 6','needed seaborn.
required pytorch.
plus pandas.
desirable excel.
not needed git.
not required kubernetes','created manually synthetic',NULL,'2026-10-17','Considering');
INSERT INTO "jobs" VALUES(7,'job 7 synthetic','Python and SQL are required.
Docker is not needed.
Python und SQL sind von Vorteil.','created manually synthetic',NULL,'2026-10-17','Considering');
INSERT INTO "jobs" VALUES(8,'Fictional demo - Praktikum Datenwissenschaft','Entwickle Modelle für maschinelles Lernen mit Python.
Werte Experimente aus und dokumentiere die Ergebnisse.','created manually synthetic',NULL,'2026-10-17','Not applied');
INSERT INTO "jobs" VALUES(9,'fict-helloo','hi how are you
i need freelancer with python experience
i also need sql and aws and powerbi experienced guy','lienkdein',NULL,'2026-10-17','Not applied');
INSERT INTO "jobs" VALUES(10,'hey_jobs 33245','We need Python.

We need a developer with Python and SQL experience.

Experience with Python and SQL is required.

Kenntnisse in Python und SQL sind erforderlich.','noted_ger_aus_swt',NULL,'2026-10-18','Not applied');
INSERT INTO "jobs" VALUES(11,'Demo A','AWS is required.','hugy',NULL,'2026-10-18','Not applied');
INSERT INTO "jobs" VALUES(12,'Demo B','Python is required.','hugy',NULL,'2026-10-18','Not applied');
INSERT INTO "jobs" VALUES(13,'Demo C','AWS is not required.','hugy',NULL,'2026-10-18','Closed');
INSERT INTO "jobs" VALUES(14,'sep. fict test 1','Python is required. Python is required.','fict 1',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(15,'sep. fict test 2','Python and SQL are required.','fict list 2',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(16,'sep. fict test 3','Docker is not required. SQL is required.','fict list 3',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(17,'fict listing 4','Python is required. 
Python is desirable.','list 4',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(18,'fictional list 5','Python is desirable. 
Rust is required.','list 5',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(19,'german comp. incl. bavaria','German B2 is required. 
English is desirable.','germany ',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(20,'state change','python is not required','reg.',NULL,'2026-10-20','Not applied');
INSERT INTO "jobs" VALUES(21,'java developer','i need a guy experienced in java and javascript','developer .co',NULL,'2026-10-21','Not applied');
INSERT INTO "jobs" VALUES(22,'nlp engineer ','all the nlp concepts are required. 
transformers, hugging face, llms knowledge is needed.
python, sql, aws, powerbi are a plus.
strictly need someone with experience in agentic ai, prompt engineering','po&b amerika',NULL,'2026-10-21','Not applied');
INSERT INTO "jobs" VALUES(23,'AI Engineer','transformers, hugging face, llms knowledge is needed.
python, sql, aws, powerbi are a plus.
strictly need someone with experience in agentic ai, prompt engineering','chatgpt deepseek',NULL,'2026-10-22','Not applied');
CREATE TABLE navigator_catalogue_v3 (
            version TEXT PRIMARY KEY, sha256 TEXT NOT NULL,
            provenance TEXT NOT NULL, review_status TEXT NOT NULL, loaded_at TEXT NOT NULL);
INSERT INTO "navigator_catalogue_v3" VALUES('project-catalogue-0.3.0','6c3c2ef745fed9d67b425cb6a652a63537957868dfae4f408ab9c0a212c6f678','Project-authored explicit terms. No externally verified ESCO mappings. Needs corpus-based human review.','draft_internal_checks_only','2026-10-16T20:25:39.904872+00:00');
INSERT INTO "navigator_catalogue_v3" VALUES('project-catalogue-0.3.1','258719c3d56fafea931e00b8ed1eaeee1559897db9421c74a1f7a9153a2fe04a','Project-authored explicit terms. No externally verified ESCO mappings. Needs corpus-based human review.','draft_internal_checks_only','2026-10-18T11:55:22.144814+00:00');
CREATE TABLE navigator_language_reviews_v4(job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,source_hash TEXT NOT NULL,language TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('required','desirable','not_required','uncertain')),reason TEXT NOT NULL,automatic_json TEXT NOT NULL,reviewed_at TEXT NOT NULL,PRIMARY KEY(job_id,source_hash,language,start_offset,end_offset));
CREATE TABLE navigator_languages_v2 (
                candidate_id INTEGER NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
                language TEXT NOT NULL,
                reported_level TEXT NOT NULL,
                note TEXT NOT NULL,
                PRIMARY KEY(candidate_id, language)
            );
INSERT INTO "navigator_languages_v2" VALUES(1,'German','A1','Learning');
INSERT INTO "navigator_languages_v2" VALUES(1,'French','Not specified','Learning');
INSERT INTO "navigator_languages_v2" VALUES(1,'English','C1','expert');
CREATE TABLE navigator_metadata_v3 (
            job_id INTEGER PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
            company TEXT NOT NULL, location TEXT NOT NULL,
            work_type TEXT NOT NULL, source_language TEXT NOT NULL);
INSERT INTO "navigator_metadata_v3" VALUES(2,'tierrr','trier','werk-student','english');
INSERT INTO "navigator_metadata_v3" VALUES(4,'amazon','luxembourg','internship','english');
INSERT INTO "navigator_metadata_v3" VALUES(5,'happy dec..inc..','saarburg','werk-student','german');
INSERT INTO "navigator_metadata_v3" VALUES(6,'trust partner obian','luxembourg','internship','french');
INSERT INTO "navigator_metadata_v3" VALUES(7,'aizon','mainz','internship','english');
INSERT INTO "navigator_metadata_v3" VALUES(8,'praktikum','berlin','internship','german');
INSERT INTO "navigator_metadata_v3" VALUES(9,'koo','erlangen','werk-student','english');
INSERT INTO "navigator_metadata_v3" VALUES(10,'gapp','interlaken','full-time','english');
INSERT INTO "navigator_metadata_v3" VALUES(14,'','','','');
INSERT INTO "navigator_metadata_v3" VALUES(15,'','','','');
INSERT INTO "navigator_metadata_v3" VALUES(16,'','','','');
INSERT INTO "navigator_metadata_v3" VALUES(17,'amr','','werk-student','english');
INSERT INTO "navigator_metadata_v3" VALUES(18,'amr','berlin','internship','english');
INSERT INTO "navigator_metadata_v3" VALUES(19,'swiss-german-austria','salzburg','permanent','english');
INSERT INTO "navigator_metadata_v3" VALUES(20,'','','','');
INSERT INTO "navigator_metadata_v3" VALUES(21,'working actually','heilbronn','full-time','english');
INSERT INTO "navigator_metadata_v3" VALUES(22,'po&b amerika co incl','new york','fulltime','english');
INSERT INTO "navigator_metadata_v3" VALUES(23,'gpt','denver','permanent','english');
CREATE TABLE navigator_preferences_v3 (
            candidate_id INTEGER PRIMARY KEY REFERENCES candidates(candidate_id) ON DELETE CASCADE,
            payload TEXT NOT NULL);
INSERT INTO "navigator_preferences_v3" VALUES(1,'{"role_areas": ["NLP", "data sceince", "ml", "AI", "machine learning", "business analyst", "data analyst"], "locations": ["Trier", "luxembourg", "saarburg", "koblenz", "mainz", "berlin", "munich", "heilbronn", "bonn", "erlangen", "nuremberg", "frankfurt"], "work_types": ["Internship", "werk-student", "working student"]}');
CREATE TABLE navigator_reviews_v2 (
                job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                source_hash TEXT NOT NULL,
                skill_id INTEGER NOT NULL REFERENCES skills(skill_id),
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                reviewed_status TEXT NOT NULL CHECK(reviewed_status IN ('required','desirable','not_required','uncertain')),
                review_note TEXT NOT NULL,
                rule_status_at_review TEXT NOT NULL,
                rule_id_at_review TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                PRIMARY KEY(job_id, source_hash, skill_id, start_offset, end_offset)
            );
INSERT INTO "navigator_reviews_v2" VALUES(4,'bd527846b25a8cd45625f71519ab4b9f9155ed80b4dae40ef22c29f9c529b9aa',14,17,25,'required','written in desc.','required','explicit_required_v2','2026-10-18T19:48:56.006508+00:00');
INSERT INTO "navigator_reviews_v2" VALUES(4,'bd527846b25a8cd45625f71519ab4b9f9155ed80b4dae40ef22c29f9c529b9aa',16,37,42,'desirable','written in desc.','desirable','coordinated_subject_list_v1','2026-10-18T19:49:20.336654+00:00');
INSERT INTO "navigator_reviews_v2" VALUES(22,'37e0ae683762a61d1b730c1c319f9bfb1c3456cebee7eff47aa36ffd78dbb3cc',1,90,96,'desirable','writtn','uncertain','shared_clause_review','2026-10-21T17:21:03.380047+00:00');
INSERT INTO "navigator_reviews_v2" VALUES(22,'37e0ae683762a61d1b730c1c319f9bfb1c3456cebee7eff47aa36ffd78dbb3cc',2,98,101,'desirable','wr','uncertain','shared_clause_review','2026-10-21T17:21:13.495667+00:00');
INSERT INTO "navigator_reviews_v2" VALUES(22,'37e0ae683762a61d1b730c1c319f9bfb1c3456cebee7eff47aa36ffd78dbb3cc',18,103,106,'desirable','wr','uncertain','shared_clause_review','2026-10-21T17:21:23.128979+00:00');
INSERT INTO "navigator_reviews_v2" VALUES(22,'37e0ae683762a61d1b730c1c319f9bfb1c3456cebee7eff47aa36ffd78dbb3cc',14,108,115,'desirable','wr','uncertain','shared_clause_review','2026-10-21T17:21:30.136580+00:00');
CREATE TABLE navigator_wording_suggestions_v1 (
                suggestion_id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                source_sha256 TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,
                wording TEXT NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL,
                UNIQUE(job_id,source_sha256,start_offset,end_offset));
CREATE TABLE skill_aliases (
                alias TEXT PRIMARY KEY NOT NULL,
                skill_id INTEGER NOT NULL,

                CHECK (length(trim(alias)) > 0),

                FOREIGN KEY (skill_id)
                    REFERENCES skills(skill_id)
            );
INSERT INTO "skill_aliases" VALUES('python',1);
INSERT INTO "skill_aliases" VALUES('sql',2);
INSERT INTO "skill_aliases" VALUES('structured query language',2);
INSERT INTO "skill_aliases" VALUES('docker',3);
INSERT INTO "skill_aliases" VALUES('scikit-learn',4);
INSERT INTO "skill_aliases" VALUES('sklearn',4);
INSERT INTO "skill_aliases" VALUES('scikit learn',4);
INSERT INTO "skill_aliases" VALUES('pandas',5);
INSERT INTO "skill_aliases" VALUES('numpy',6);
INSERT INTO "skill_aliases" VALUES('pytorch',7);
INSERT INTO "skill_aliases" VALUES('tensorflow',8);
INSERT INTO "skill_aliases" VALUES('git',9);
INSERT INTO "skill_aliases" VALUES('linux',10);
INSERT INTO "skill_aliases" VALUES('postgresql',11);
INSERT INTO "skill_aliases" VALUES('postgres',11);
INSERT INTO "skill_aliases" VALUES('mysql',12);
INSERT INTO "skill_aliases" VALUES('sqlite',13);
INSERT INTO "skill_aliases" VALUES('power bi',14);
INSERT INTO "skill_aliases" VALUES('tableau',15);
INSERT INTO "skill_aliases" VALUES('microsoft excel',16);
INSERT INTO "skill_aliases" VALUES('excel',16);
INSERT INTO "skill_aliases" VALUES('kubernetes',17);
INSERT INTO "skill_aliases" VALUES('k8s',17);
INSERT INTO "skill_aliases" VALUES('amazon web services',18);
INSERT INTO "skill_aliases" VALUES('aws',18);
INSERT INTO "skill_aliases" VALUES('microsoft azure',19);
INSERT INTO "skill_aliases" VALUES('azure',19);
INSERT INTO "skill_aliases" VALUES('hugging face transformers',20);
INSERT INTO "skill_aliases" VALUES('pyspark',21);
INSERT INTO "skill_aliases" VALUES('apache spark',22);
INSERT INTO "skill_aliases" VALUES('apache airflow',23);
INSERT INTO "skill_aliases" VALUES('fastapi',24);
INSERT INTO "skill_aliases" VALUES('flask',25);
INSERT INTO "skill_aliases" VALUES('mlflow',26);
INSERT INTO "skill_aliases" VALUES('jupyter',27);
INSERT INTO "skill_aliases" VALUES('jupyter notebook',27);
INSERT INTO "skill_aliases" VALUES('matplotlib',28);
INSERT INTO "skill_aliases" VALUES('seaborn',29);
INSERT INTO "skill_aliases" VALUES('plotly',30);
INSERT INTO "skill_aliases" VALUES('scipy',31);
INSERT INTO "skill_aliases" VALUES('spacy',32);
INSERT INTO "skill_aliases" VALUES('nltk',33);
INSERT INTO "skill_aliases" VALUES('opencv',34);
INSERT INTO "skill_aliases" VALUES('xgboost',35);
INSERT INTO "skill_aliases" VALUES('lightgbm',36);
INSERT INTO "skill_aliases" VALUES('mongodb',37);
INSERT INTO "skill_aliases" VALUES('elasticsearch',38);
INSERT INTO "skill_aliases" VALUES('bigquery',39);
INSERT INTO "skill_aliases" VALUES('google bigquery',39);
INSERT INTO "skill_aliases" VALUES('snowflake',40);
INSERT INTO "skill_aliases" VALUES('databricks',41);
INSERT INTO "skill_aliases" VALUES('natural language processing',42);
INSERT INTO "skill_aliases" VALUES('natürliche sprachverarbeitung',42);
INSERT INTO "skill_aliases" VALUES('nlp',42);
INSERT INTO "skill_aliases" VALUES('machine learning',43);
INSERT INTO "skill_aliases" VALUES('maschinelles lernen',43);
INSERT INTO "skill_aliases" VALUES('deep learning',44);
INSERT INTO "skill_aliases" VALUES('computer vision',45);
INSERT INTO "skill_aliases" VALUES('data analysis',46);
INSERT INTO "skill_aliases" VALUES('datenanalyse',46);
INSERT INTO "skill_aliases" VALUES('data visualization',47);
INSERT INTO "skill_aliases" VALUES('data visualisation',47);
INSERT INTO "skill_aliases" VALUES('datenvisualisierung',47);
INSERT INTO "skill_aliases" VALUES('statistics',48);
INSERT INTO "skill_aliases" VALUES('statistik',48);
INSERT INTO "skill_aliases" VALUES('information retrieval',49);
INSERT INTO "skill_aliases" VALUES('large language model',50);
INSERT INTO "skill_aliases" VALUES('large language models',50);
INSERT INTO "skill_aliases" VALUES('llms',50);
INSERT INTO "skill_aliases" VALUES('retrieval augmented generation',51);
INSERT INTO "skill_aliases" VALUES('retrieval-augmented generation',51);
INSERT INTO "skill_aliases" VALUES('powerbi',14);
INSERT INTO "skill_aliases" VALUES('java',52);
INSERT INTO "skill_aliases" VALUES('javascript',53);
INSERT INTO "skill_aliases" VALUES('java script',53);
INSERT INTO "skill_aliases" VALUES('java-script',53);
INSERT INTO "skill_aliases" VALUES('agentic ai',54);
INSERT INTO "skill_aliases" VALUES('prompt engineering',55);
INSERT INTO "skill_aliases" VALUES('hugging face',56);
INSERT INTO "skill_aliases" VALUES('transformers',57);
INSERT INTO "skill_aliases" VALUES('agents',54);
CREATE TABLE skills (
                skill_id INTEGER PRIMARY KEY,
                skill_key TEXT NOT NULL UNIQUE,
                canonical_name TEXT NOT NULL,
                esco_uri TEXT UNIQUE
            );
INSERT INTO "skills" VALUES(1,'python','Python',NULL);
INSERT INTO "skills" VALUES(2,'sql','SQL',NULL);
INSERT INTO "skills" VALUES(3,'docker','Docker',NULL);
INSERT INTO "skills" VALUES(4,'scikit-learn','Scikit-learn',NULL);
INSERT INTO "skills" VALUES(5,'pandas','pandas',NULL);
INSERT INTO "skills" VALUES(6,'numpy','NumPy',NULL);
INSERT INTO "skills" VALUES(7,'pytorch','PyTorch',NULL);
INSERT INTO "skills" VALUES(8,'tensorflow','TensorFlow',NULL);
INSERT INTO "skills" VALUES(9,'git','Git',NULL);
INSERT INTO "skills" VALUES(10,'linux','Linux',NULL);
INSERT INTO "skills" VALUES(11,'postgresql','PostgreSQL',NULL);
INSERT INTO "skills" VALUES(12,'mysql','MySQL',NULL);
INSERT INTO "skills" VALUES(13,'sqlite','SQLite',NULL);
INSERT INTO "skills" VALUES(14,'power-bi','Power BI',NULL);
INSERT INTO "skills" VALUES(15,'tableau','Tableau',NULL);
INSERT INTO "skills" VALUES(16,'excel','Excel',NULL);
INSERT INTO "skills" VALUES(17,'kubernetes','Kubernetes',NULL);
INSERT INTO "skills" VALUES(18,'aws','Amazon Web Services',NULL);
INSERT INTO "skills" VALUES(19,'azure','Microsoft Azure',NULL);
INSERT INTO "skills" VALUES(20,'hugging-face-transformers','Hugging Face Transformers',NULL);
INSERT INTO "skills" VALUES(21,'pyspark','PySpark',NULL);
INSERT INTO "skills" VALUES(22,'apache-spark','Apache Spark',NULL);
INSERT INTO "skills" VALUES(23,'apache-airflow','Apache Airflow',NULL);
INSERT INTO "skills" VALUES(24,'fastapi','FastAPI',NULL);
INSERT INTO "skills" VALUES(25,'flask','Flask',NULL);
INSERT INTO "skills" VALUES(26,'mlflow','MLflow',NULL);
INSERT INTO "skills" VALUES(27,'jupyter','Jupyter',NULL);
INSERT INTO "skills" VALUES(28,'matplotlib','Matplotlib',NULL);
INSERT INTO "skills" VALUES(29,'seaborn','Seaborn',NULL);
INSERT INTO "skills" VALUES(30,'plotly','Plotly',NULL);
INSERT INTO "skills" VALUES(31,'scipy','SciPy',NULL);
INSERT INTO "skills" VALUES(32,'spacy','spaCy',NULL);
INSERT INTO "skills" VALUES(33,'nltk','NLTK',NULL);
INSERT INTO "skills" VALUES(34,'opencv','OpenCV',NULL);
INSERT INTO "skills" VALUES(35,'xgboost','XGBoost',NULL);
INSERT INTO "skills" VALUES(36,'lightgbm','LightGBM',NULL);
INSERT INTO "skills" VALUES(37,'mongodb','MongoDB',NULL);
INSERT INTO "skills" VALUES(38,'elasticsearch','Elasticsearch',NULL);
INSERT INTO "skills" VALUES(39,'bigquery','BigQuery',NULL);
INSERT INTO "skills" VALUES(40,'snowflake','Snowflake',NULL);
INSERT INTO "skills" VALUES(41,'databricks','Databricks',NULL);
INSERT INTO "skills" VALUES(42,'natural-language-processing','Natural language processing',NULL);
INSERT INTO "skills" VALUES(43,'machine-learning','Machine learning',NULL);
INSERT INTO "skills" VALUES(44,'deep-learning','Deep learning',NULL);
INSERT INTO "skills" VALUES(45,'computer-vision','Computer vision',NULL);
INSERT INTO "skills" VALUES(46,'data-analysis','Data analysis',NULL);
INSERT INTO "skills" VALUES(47,'data-visualisation','Data visualisation',NULL);
INSERT INTO "skills" VALUES(48,'statistics','Statistics',NULL);
INSERT INTO "skills" VALUES(49,'information-retrieval','Information retrieval',NULL);
INSERT INTO "skills" VALUES(50,'large-language-models','Large language models',NULL);
INSERT INTO "skills" VALUES(51,'retrieval-augmented-generation','Retrieval-augmented generation',NULL);
INSERT INTO "skills" VALUES(52,'user-4a690170cd9d4cf18cdad3b3f88ac085','java',NULL);
INSERT INTO "skills" VALUES(53,'user-c11f5cf807a741b79929568d6ed62635','javascript',NULL);
INSERT INTO "skills" VALUES(54,'user-f0ce163156b94215aa6bc0a67d71b9de','Agentic AI',NULL);
INSERT INTO "skills" VALUES(55,'user-8442b8b9e457413f9bb4b0fbdba4167e','Prompt Engineering',NULL);
INSERT INTO "skills" VALUES(56,'user-ceeee1efa81945daa8a22ca028194142','Hugging Face',NULL);
INSERT INTO "skills" VALUES(57,'user-6884f6c4913a4351a6df06f91f414128','Transformers',NULL);
COMMIT;
