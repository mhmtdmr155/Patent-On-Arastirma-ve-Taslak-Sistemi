from streamlit.testing.v1 import AppTest

code = """
import streamlit as st
r = st.radio("Choose", ["0 - Irrelevant", "1 - Partial", "2 - Direct"], index=None, key="my_radio")
if st.button("Save"):
    if r is None:
        st.error("Please make a selection!")
    else:
        st.success(f"Saved: {r}")
"""

at = AppTest.from_string(code)
at.run()
print("INITIAL RADIO VALUE:", repr(at.radio[0].value))
at.button[0].click().run()
print("ERROR MESSAGE SHOWN:", [e.value for e in at.error])

# Now select an option
at.radio[0].set_value("0 - Irrelevant").run()
at.button[0].click().run()
print("SUCCESS MESSAGE SHOWN:", [s.value for s in at.success])

