import streamlit as st

from src import queries
from src.services import UserRegistration, register_user, set_user_active
from src.ui import require_role, setup_page, show_dataframe


setup_page("사용자 관리")
require_role("ADMIN")
st.title("🛡️사용자 관리")
st.markdown("---")

tab_create, tab_list = st.tabs(["신규 계정 등록", "계정 조회 / 활성화 관리"])

with tab_create:
    if "last_user_created" in st.session_state:
        st.success("계정이 등록되었습니다.")
        st.write(st.session_state.pop("last_user_created"))

    with st.form("user_create_form"):
        new_user_id = st.text_input("아이디")
        new_user_name = st.text_input("이름")
        new_password = st.text_input("비밀번호 (4자 이상)", type="password")
        new_role = st.selectbox("권한", ["OPERATOR", "INSPECTOR", "ADMIN"])

        create_submitted = st.form_submit_button("계정 등록", type="primary")

    if create_submitted:
        data = UserRegistration(
            user_id=new_user_id,
            user_name=new_user_name,
            password=new_password,
            role=new_role,
        )
        try:
            result = register_user(data)
            st.session_state["last_user_created"] = result
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

with tab_list:
    users_df = queries.all_users()
    show_dataframe(users_df, "등록된 사용자가 없습니다.")

    if not users_df.empty:
        st.markdown("---")
        toggle_options = {
            f"{row['user_id']} | {row['user_name']} | {row['role']} "
            f"({'사용' if row['is_active'] == 'Y' else '비활성'})": row
            for _, row in users_df.iterrows()
        }
        toggle_label = st.selectbox("사용여부 변경할 계정", list(toggle_options.keys()))
        toggle_row = toggle_options[toggle_label]

        if toggle_row["user_id"] == st.session_state.get("user_id"):
            st.info("현재 로그인한 계정 본인은 여기서 비활성화할 수 없습니다.")
        else:
            new_status = "N" if toggle_row["is_active"] == "Y" else "Y"
            action_label = "비활성화" if new_status == "N" else "다시 활성화"
            if st.button(f"{toggle_row['user_id']} {action_label}"):
                try:
                    set_user_active(toggle_row["user_id"], new_status)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

st.markdown("---")
