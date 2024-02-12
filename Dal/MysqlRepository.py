import mysql.connector as mysql


class MysqlRepository:

    def __init__(self):
        self._user = 'user'
        self._password = 'password'
        self._database = 'link_db'
        self._host = '127.0.0.1'
        self._port = 3306

    def get_tracked_subdomains(self, domain) -> set:
        self.__init_connection()

        self._cursor.execute("CREATE TABLE IF NOT EXISTS TrackDomains "
                             "(id INT AUTO_INCREMENT PRIMARY KEY, domain VARCHAR(255), found_domains VARCHAR(10000))")

        self._cursor.execute(f"SELECT found_domains FROM TrackDomains WHERE domain = '{domain}'")

        found_domains = set()
        for row in self._cursor.fetchall():
            found_domains.update(set(str(row)
                                     .replace("(", "")
                                     .replace(",)", "")
                                     .replace("\"", "")
                                     .replace("\'", "")
                                     .split(';')))

        self._cnx.commit()
        self.__close_connection()

        return found_domains

    def save_tracker_result(self, domain: str, new_urls: set):
        found_domains = ";".join(new_urls)

        self.__init_connection()
        self._cursor.execute(f"INSERT INTO TrackDomains (domain, found_domains) VALUES ('{domain}', '{found_domains}');")
        self._cnx.commit()
        self.__close_connection()

    def __init_connection(self):
        try:
            self._cnx = mysql.connect(
                user=self._user,
                password=self._password,
                database=self._database,
                host=self._host,
                port=self._port
            )
            self._cursor = self._cnx.cursor()

        except mysql.Error as err:
            print("Error connecting to MySQL:", err)

    def __close_connection(self):
        self._cursor.close()
        self._cnx.close()
