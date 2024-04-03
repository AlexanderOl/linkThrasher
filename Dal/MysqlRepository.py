import mysql.connector as mysql


class MysqlRepository:

    def __init__(self):
        self._user = 'user'
        self._password = 'password'
        self._database = 'link_db'
        self._host = '127.0.0.1'
        self._port = 3306

    def init_tables(self):
        self.__init_connection()

        self._cursor.execute("CREATE TABLE IF NOT EXISTS TrackDomains "
                             "(id INT AUTO_INCREMENT PRIMARY KEY, domain VARCHAR(255), found_domains TEXT)")

        self._cursor.execute("CREATE TABLE IF NOT EXISTS TrackUrls "
                             "(id INT AUTO_INCREMENT PRIMARY KEY, domain VARCHAR(255), found_urls TEXT)")
        self._cnx.commit()
        self.__close_connection()

    def get_tracked_subdomains(self, domain) -> set:
        self.__init_connection()

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

    def get_tracked_urls(self, domain) -> set:
        self.__init_connection()

        self._cursor.execute(f"SELECT found_urls FROM TrackUrls WHERE domain = '{domain}'")

        found_urls = set()
        for row in self._cursor.fetchall():
            found_urls.update(set(str(row)
                                  .replace("(", "")
                                  .replace(",)", "")
                                  .replace("\"", "")
                                  .replace("\'", "")
                                  .split(';')))

        self._cnx.commit()
        self.__close_connection()

        return found_urls

    def save_tracker_domains_result(self, domain: str, new_domains: set):
        found_domains = ";".join(new_domains)

        self.__init_connection()
        self._cursor.execute(f"INSERT INTO TrackDomains (domain,found_domains) VALUES ('{domain}','{found_domains}');")
        self._cnx.commit()
        self.__close_connection()

    def save_tracker_urls_result(self, domain: str, new_urls: set):
        found_urls = ";".join(new_urls)

        self.__init_connection()
        self._cursor.execute(f"INSERT INTO TrackUrls (domain,found_urls) VALUES ('{domain}','{found_urls}');")
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
