import getpass

from src.db import get_connection
from src.auth import hash_password


def main():
    connection = get_connection()
    try:
        existing = connection.execute(
            "SELECT COUNT(*) AS cnt FROM user"
        ).fetchone()
        if existing["cnt"] > 0:
            print(f"이미 사용자 계정이 {existing['cnt']}개 존재합니다. 계속 진행하시겠습니까? (y/N)")
            if input().strip().lower() != "y":
                print("취소되었습니다.")
                return

        print("=== 최초 관리자 계정 생성 ===")
        user_id = input("아이디: ").strip()
        user_name = input("이름: ").strip()
        password = getpass.getpass("비밀번호 (입력 시 화면에 표시 안 됨): ")
        password_confirm = getpass.getpass("비밀번호 확인: ")

        if not user_id or not user_name:
            print("아이디와 이름은 비워둘 수 없습니다.")
            return
        if password != password_confirm:
            print("비밀번호가 일치하지 않습니다.")
            return
        if len(password) < 4:
            print("비밀번호는 4자 이상이어야 합니다.")
            return

        connection.execute(
            """
            INSERT INTO user (user_id, user_name, password_hash, role, is_active)
            VALUES (?, ?, ?, 'ADMIN', 'Y')
            """,
            (user_id, user_name, hash_password(password)),
        )
        connection.commit()
        print(f"관리자 계정 '{user_id}'가 생성되었습니다.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()