import os
import datetime
import urllib
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class DesktopFile(Base):
    __tablename__ = 'desktop_files'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255)) 
    file_path = Column(String(500))
    file_size = Column(BigInteger) 
    last_modified = Column(DateTime)

params = urllib.parse.quote_plus(
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=YOUR_SERVER_NAME;'
    r'DATABASE=YOUR_DATABASE;'
    r'Trusted_Connection=yes;'
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

class AdminManager:
    def __init__(self):
        self.desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    def sync_data(self):
        """Синхронизирует файлы на диске с записями в БД."""
        try:
            session.query(DesktopFile).delete()
            
            files_found = 0
            if not os.path.exists(self.desktop_path):
                return "Рабочий стол не найден."

            for item in os.listdir(self.desktop_path):
                full_path = os.path.join(self.desktop_path, item)
                
                if os.path.isfile(full_path):
                    stats = os.stat(full_path)
                    new_entry = DesktopFile(
                        filename=item,
                        file_path=full_path,
                        file_size=stats.st_size,
                        last_modified=datetime.datetime.fromtimestamp(stats.st_mtime)
                    )
                    session.add(new_entry)
                    files_found += 1
            
            session.commit()
            return f"Успешно! В SQL Server внесено: {files_found} файлов."
        except Exception as e:
            session.rollback()
            return f"Ошибка при синхронизации: {e}"

    def get_all_files(self):
        return session.query(DesktopFile).all()

    def remove_file(self, file_id):
        """Удаляет файл физически и из БД."""
        file_obj = session.query(DesktopFile).filter_by(id=file_id).first()
        if not file_obj:
            return "Файл с таким ID не найден."

        try:
            if os.path.exists(file_obj.file_path):
                os.remove(file_obj.file_path)
                status = f"Файл '{file_obj.filename}' удален физически и из SQL Server."
            else:
                status = f"Файл не найден на диске, удален только из базы."
            
            session.delete(file_obj)
            session.commit()
            return status
        except Exception as e:
            session.rollback()
            return f"Не удалось удалить файл: {e}"

def run_admin_panel():
    manager = AdminManager()
    while True:
        print("\n" + "="*45)
        print("   SQL SERVER АДМИН-ПАНЕЛЬ (DESKTOP)   ")
        print("="*45)
        print("1. Обновить список файлов (Sync)")
        print("2. Просмотреть список файлов")
        print("3. Удалить файл по ID")
        print("4. Выйти")
        
        choice = input("\nВыбери опцию: ").strip()

        if choice == '1':
            print(manager.sync_data())
        elif choice == '2':
            files = manager.get_all_files()
            if not files:
                print("База пуста.")
                continue
            print(f"\n{'ID':<4} | {'Имя файла':<30} | {'Размер (КБ)':<10}")
            print("-" * 50)
            for f in files:
                kb_size = f.file_size / 1024
                name = (f.filename[:27] + '..') if len(f.filename) > 30 else f.filename
                print(f"{f.id:<4} | {name:<30} | {kb_size:.2f}")
        elif choice == '3':
            try:
                fid = int(input("Введите ID: "))
                if input(f"Удалить {fid}? (y/n): ").lower() == 'y':
                    print(manager.remove_file(fid))
            except ValueError:
                print("Ошибка: ID должен быть числом.")
        elif choice == '4':
            break

if __name__ == "__main__":
    run_admin_panel()
