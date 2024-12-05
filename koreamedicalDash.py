import pandas as pd
import folium
import streamlit as st
from streamlit_folium import folium_static
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.express as px

# 엑셀 파일 경로 설정
url="https://raw.githubusercontent.com/seungjuniper/koreamedicalDash/main/final.xlsx" 

# 엑셀 파일을 DataFrame으로 읽기
df = pd.read_excel(url)

# 숫자형 데이터 처리
for col in ["인구 10만명 당 병상수", "인구 10만명 당 병원수", "인구 10만명 당 의사수", "미충족의료율", "의료접근성지표", "전공불균형지표"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)

# 페이지 기본 설정
st.set_page_config(page_title="의료 현황 대시보드", layout="wide", page_icon="🏥")

# 타이틀
st.header('전국 의료 현황 대시보드📈', divider='gray')

# 데이터 필터링 및 기본 변수 초기화
selected_region = st.selectbox("시도 선택", options=["전국"] + df["시도"].unique().tolist(), index=0)
selected_city = None  # 초기값 설정

if selected_region == "전국":
    filtered_df = df.copy()
else:
    filtered_df = df[df["시도"] == selected_region]
    selected_city = st.selectbox("시군구 선택", options=["전체"] + filtered_df["시군구"].unique().tolist(), index=0)
    if selected_city != "전체":
        filtered_df = filtered_df[filtered_df["시군구"] == selected_city]

# **지표 선택 버튼 추가**
indicator = st.radio("지표를 선택하세요:", ['의료접근성지표', '전공불균형지표'], help="의료접근성 지표 계산 방법:인구 10만 명 당 의사수/병원수/병상수/미충족 의료율 정규화 후 25점씩 가중치 부여해 100점 만점 | 전공불균형 지표 계산 방법: 해당 지역의 필수과 비율 - 0.38", label_visibility="visible")

# 주요 지표 표시 (컨테이너 사용)
with st.container():
    st.markdown("### 주요 지표")
    cols = st.columns(3)

    # 주요 지표 정의
    metrics = [
        ("인구 10만명 당 의사수", "인구 10만명 당 의사수"),
        ("인구 10만명 당 병원수", "인구 10만명 당 병원수"),
        ("인구 10만명 당 병상수", "인구 10만명 당 병상수"),
        ("미충족의료율", "미충족의료율"),
        ("의료접근성 지표", "의료접근성지표"),
        ("전공불균형 지표", "전공불균형지표"),
    ]

    for i, (metric, col_name) in enumerate(metrics):
        col = cols[i % 3]

        # 지표 컬럼 존재 확인
        if col_name not in filtered_df.columns:
            col.error(f"{col_name} 데이터가 없습니다.")
            continue

        # NaN 또는 데이터 없는 경우 처리
        if filtered_df[col_name].isna().all():
            col.error(f"{metric} 데이터가 없습니다.")
            continue

        # 비교 기준 설정
        if selected_city == "전체" and selected_region != "전국":  # 시도 선택 시 전국과 비교
            avg_value = df[col_name].mean()
            current_value = filtered_df[col_name].mean()
            help_text = f"비교 기준: 전국 평균 {avg_value:.2f}"
        elif selected_city != "전체":  # 시군구 선택 시 시도의 평균과 비교
            avg_value = df[df["시도"] == selected_region][col_name].mean()
            current_value = filtered_df[col_name].mean()
            help_text = f"비교 기준: {selected_region} 평균 {avg_value:.2f}"
        else:  # 전국 선택
            avg_value = df[col_name].mean()
            current_value = filtered_df[col_name].mean()
            help_text = f"비교 기준: 전국 평균 {avg_value:.2f}"

        # 값이 없는 경우 대비
        if pd.isna(current_value):
            col.metric(label=metric, value="N/A", delta="N/A", help=help_text)
            continue

        # Delta 계산
        delta = current_value - avg_value
        delta_text = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"

        # Delta NaN일 경우 0으로 설정
        if pd.isna(delta):
            delta_text = "+0.00"

        # Metric 표시
        col.metric(
            label=metric,
            value=f"{current_value:.2f}",
            delta=delta_text,
            help=help_text
        )

# 지도 생성 (선택된 데이터에 맞춰 중심 설정)
if selected_region == "전국":
    center = [37.5665, 126.978]  # 서울 중심
    zoom_start = 7  # 전국 확대
elif selected_city == "전체":
    center = [filtered_df["위도"].mean(), filtered_df["경도"].mean()]  # 선택된 시도의 중심
    zoom_start = 10  # 시도 확대
else:
    center = [filtered_df["위도"].iloc[0], filtered_df["경도"].iloc[0]]  # 선택된 시군구의 중심
    zoom_start = 12  # 시군구 확대

m = folium.Map(location=center, zoom_start=zoom_start)

# 색상 설정 함수
def get_color(value, vmin, vmax):
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.cm.get_cmap('coolwarm')
    rgba_color = cmap(norm(value))
    return mcolors.to_hex(rgba_color)

# 선택한 지표에 따라 지도 표시
vmin, vmax = filtered_df[indicator].min(), filtered_df[indicator].max()
for _, row in filtered_df.iterrows():
    lat, lon, value = row["위도"], row["경도"], row[indicator]
    folium.CircleMarker(
        location=[lat, lon],
        radius=10,
        color=get_color(value, vmin, vmax),
        fill=True,
        fill_color=get_color(value, vmin, vmax),
        fill_opacity=0.7,
        popup=f"{row['시도']} {row['시군구']} - {value:.2f}"
    ).add_to(m)

# 필수과/비필수과 비율 계산
mandatory_cols = ["내과", "외과", "심장혈관흉부외과", "산부인과", "소아청소년과"]
filtered_df[mandatory_cols] = filtered_df[mandatory_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
total_optional = filtered_df["비필수과"].sum()
total_mandatory = filtered_df[mandatory_cols].sum().sum()

# 파이차트 데이터
labels = ["비필수과"] + mandatory_cols
values = [total_optional] + [filtered_df[col].sum() for col in mandatory_cols]
fig1 = px.pie(
    names=labels,
    values=values,
    title=f"{selected_region}의 필수과/비필수과 비율" if selected_city == "전체" or selected_city is None else f"{selected_city}의 필수과/비필수과 비율"
)

# 바 차트 데이터
pop_col = "시도" if selected_region == "전국" else "시군구"
pop_data = filtered_df.groupby(pop_col)["인구수"].sum().reset_index()
fig2 = px.bar(
    pop_data,
    x=pop_col,
    y="인구수",
    labels={"인구수": "인구수"},
    title=f"{selected_region}의 인구 분포" if selected_city == "전체" or selected_city is None else f"{selected_city}의 인구 분포"
)

# 지도 및 차트 시각화
with st.container():
    st.markdown("---")
    st.markdown(
        "#### 지표 시각화",
        help="색상은 선택한 지표 값에 따라 표시됩니다. 값이 높을수록 빨간색에 가깝고, 낮을수록 파란색에 가깝습니다."
    )
    folium_static(m, width=1500, height=600)

    # 하단: 바 차트와 파이 차트를 나란히 배치
    bottom_col1, bottom_col2 = st.columns([1, 1])
    with bottom_col1:
        st.plotly_chart(fig2, use_container_width=True)
    with bottom_col2:
        st.plotly_chart(fig1, use_container_width=True)
