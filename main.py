import pandas as pd
import streamlit as st
import numpy as np
import math
from PIL import Image
from io import BytesIO
from streamlit_option_menu import option_menu

# Interactive Table
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode


def aggrid_interactive_table(df: pd.DataFrame):
    """Creates an st-aggrid interactive table based on a dataframe.

    Args:
        df (pd.DataFrame]): Source dataframe

    Returns:
        dict: The selected row
    """
    options = GridOptionsBuilder.from_dataframe(
        df, enableRowGroup=True, enableValue=True, enablePivot=True
    )

    options.configure_side_bar()

    options.configure_selection("single")
    selection = AgGrid(
        df,
        enable_enterprise_modules=True,
        gridOptions=options.build(),
        theme="light",
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
    )

    return selection


from pyxlsb import open_workbook as open_xlsb


# M/M/c Queue is a Queue with only `c` servers and an infinite buffer.
# Detail Definition of M/M/c Queue: https://en.wikipedia.org/wiki/M/M/c_queue
#
# The inter-arrival time of the packets is a Possion R.V., while  The serving
# time of a packet is a Exponential R.V..
#
# If a packet comes and there is at least one idle server, this packet would
# be served by one server. If a packet comes and there is no idle server, this
# packet would be dropped or blocked.
#
# Basic Parameter of M/M/c/c queue:
#   1. Packet Arrival Rate: `arrival`, the parameter of Possion R.V.
#   2. Packet Serving Rate: `departure`, the parameter of Expo R.V.

class MMcQueue(object):
    def __init__(self, arrival, departure, capacity):
        """
        Given the parameter of one M/M/c/c Queue,
        initialize the queue with these parameter and calculate some parameters.
        `_rou`:     Server Utilization
        `_p0`:      Probability of that there is no packets in the queue
        `_pc`:      Probability of that there is exactly `capacity` packets in the queue,
                    that is, all the server is busy.
        `_probSum`:  p0 + p1 + p2 + ... pc - pc
        `_finalTerm`: 1/(c!) * (arrival / departure)^c
        """
        if capacity * departure <= arrival:
            raise ValueError("This Queue is unstable with the Input Parameters!!!")
        self._arrival = float(arrival)
        self._departure = float(departure)
        self._capacity = capacity
        self._rou = self._arrival / self._departure / self._capacity

        # init the parameter as if the capacity == 0
        powerTerm = 1.0
        factorTerm = 1.0
        preSum = 1.0
        # Loop through `1` to `self._capacity` to get each term and preSum
        for i in range(1, self._capacity + 1):
            powerTerm *= self._arrival / self._departure
            factorTerm /= i
            preSum += powerTerm * factorTerm
        self._finalTerm = powerTerm * factorTerm
        preSum -= self._finalTerm
        self._p0 = 1.0 / (preSum + self._finalTerm / (1 - self._rou))
        self._pc = self._finalTerm * self._p0
        self._probSum = preSum * self._p0

    def arrival(self):
        return self._arrival

    def departure(self):
        return self._departure

    def capacity(self):
        return self._capacity

    def getPk(self, k):
        """
        Return the probability when there are `k` packets in the system
        """
        if k == 0:
            return self._p0
        elif k == self._capacity:
            return self._pc
        elif k < self._capacity:
            factorTerm = 1.0 / math.factorial(k)
            powerTerm = math.pow(self._arrival / self._departure, k)
            return self._p0 * factorTerm * powerTerm
        else:
            return self._finalTerm * math.pow(self._rou, k - self._capacity) * self._p0

    def getQueueProb(self):
        """
        Return the probability when a packet comes, it needs to queue in the buffer.
        That is, P(W>0) = 1 - P(N < c)
        Also known as Erlang-C function
        """
        return 1.0 - self._probSum

    def getIdleProb(self):
        """
        Return the probability when the sever is idle.
        That is , P(N=0)
        """
        return self._p0

    def getAvgPackets(self):
        """
        Return the average number of packets in the system (in service and in the queue)
        """
        return self._rou / (1 - self._rou) * self.getQueueProb() + self._capacity * self._rou

    def getAvgQueueTime(self):
        """
        Return the average time of packets spending in the queue
        """
        return self.getQueueProb() / (self._capacity * self._departure - self._arrival)

    def getAvgQueuePacket_Given(self):
        """
        Given there is packet in the queue,
        return the average number of packets in the queue
        """
        return self._finalTerm * self._p0 / (1.0 - self._rou) / (1.0 - self._rou)

    def getAvgQueueTime_Given(self):
        """
        Given a packet must wait,
        return the average time of this packet spending in the queue
        """
        if self.getQueueProb() == 0:
            return 0
        return self.getAvgQueuePacket_Given() / (self.getQueueProb() * self._arrival)

    def getAvgResponseTime(self):
        """
        Return the average time of packets spending in the system (in service and in the queue)
        """
        return self.getAvgQueueTime() + 1.0 / self._departure

    def getAvgPacketInSystem(self):
        """
        Return the average number of packets in the system.
        """
        return self.getAvgResponseTime() * self._arrival

    def getAvgBusyServer(self):
        """
        Return the average number of busy Server.
        """
        return self.arrival / self.departure

    def getPorbWhenQueueTimeLargerThan(self, queueTime):
        """
        Return the probability when the queuing time of the packet is larger than `queueTime`
        That is P(W > queueTime) = 1 - P(W <= queueTime)
        """
        firstTerm = self._pc / (1.0 - self._rou)
        expTerm = - self._capacity * self._departure * (1.0 - self._rou) * queueTime
        secondTerm = math.exp(expTerm)
        return firstTerm * secondTerm


def queue_outputs(Fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, CLIENTE_PDV):
    # % clientes atendidos no SLA
    prob_pessoas_MED = 1 - Fila.getPorbWhenQueueTimeLargerThan(Fila.getAvgQueueTime())

    # % Clientes atendidos no tempo MAX
    prob_pessoas_MAX = 1 - Fila.getPorbWhenQueueTimeLargerThan(SLA_TEMPO_MAX)

    # Tamanho da fila:
    tamanho = Fila.getAvgPackets()
    tamanho_por_pdv = tamanho / capacity

    tamanho_asterisco = Fila.getAvgQueuePacket_Given()
    tamanho_asterisco_pdv = tamanho_asterisco / capacity

    # Tempo médio de fila:
    tempo_medio = Fila.getAvgQueueTime()
    tempo_medio_asterisco = Fila.getAvgQueueTime_Given()

    # Probabilidade tempo de espera de pessoas na fila:
    time_pessoas_fila_1_min = Fila.getPorbWhenQueueTimeLargerThan(60 / 3600)
    time_pessoas_fila_3min = Fila.getPorbWhenQueueTimeLargerThan(120 / 3600)
    time_pessoas_fila_5min = Fila.getPorbWhenQueueTimeLargerThan(180 / 3600)
    time_pessoas_fila_7min = Fila.getPorbWhenQueueTimeLargerThan(240 / 3600)
    time_pessoas_fila_7max = Fila.getPorbWhenQueueTimeLargerThan(300 / 3600)

    # Probabilidade quantidade de pessoas na fila:
    qtd_pessoas_fila_0 = Fila.getPk(0)
    qtd_pessoas_fila_1 = Fila.getPk(1)
    qtd_pessoas_fila_2 = Fila.getPk(2)
    qtd_pessoas_fila_3 = Fila.getPk(3)
    qtd_pessoas_fila_4 = Fila.getPk(4)
    qtd_pessoas_fila_5 = Fila.getPk(5)
    qtd_pessoas_fila_6 = Fila.getPk(6)
    qtd_pessoas_fila_7 = Fila.getPk(7)
    qtd_pessoas_fila_8 = Fila.getPk(8)
    qtd_pessoas_fila_9 = Fila.getPk(9)
    qtd_pessoas_fila_10 = Fila.getPk(10)
    qtd_pessoas_fila_maior_10 = 1 - (
                qtd_pessoas_fila_0 + qtd_pessoas_fila_1 + qtd_pessoas_fila_2 + qtd_pessoas_fila_3 + qtd_pessoas_fila_4 + qtd_pessoas_fila_5 + qtd_pessoas_fila_6 + qtd_pessoas_fila_7 + qtd_pessoas_fila_8 + qtd_pessoas_fila_9 + qtd_pessoas_fila_10)

    prob_qtd_pessoas_list = [qtd_pessoas_fila_0, qtd_pessoas_fila_1, qtd_pessoas_fila_2, qtd_pessoas_fila_3,
                             qtd_pessoas_fila_4, qtd_pessoas_fila_5, qtd_pessoas_fila_6, qtd_pessoas_fila_7,
                             qtd_pessoas_fila_8, qtd_pessoas_fila_9, qtd_pessoas_fila_10, qtd_pessoas_fila_maior_10]

    prob_time_list = [time_pessoas_fila_1_min, time_pessoas_fila_3min, time_pessoas_fila_5min, time_pessoas_fila_7min,
                      time_pessoas_fila_7max]

    return tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list


st.title('Pragmatis')
st.header("SMR01 - Simulador de Frente de Caixas")

with st.sidebar:
    selected = option_menu("Menu", ["Página Inicial", 'Sobre'],
                           icons=['house', 'info'], default_index=1)
if selected == "Sobre":
    st.subheader("Descrição:")
    with st.container():
        st.write(
            "Esse simulador foi desenvolvido pela Pragmatis durante o projeto SMR01 - Racionalização de despesa e o seu propósito é realizar o dimensionamento com base em diferentes com base na demanda e o tempo médio de atendimento.")

    st.subheader("Método:")
    with st.container():
        st.write(
            "O método utilizado se baseia em teoria das filas e utiliza o modelo de fila m/m/c: uma fila com 'c' servidores e capacidade infinita de fila, para maiores detalhes consultar: https://en.wikipedia.org/wiki/M/M/c_queue. Para encontrar o número ótimo de atendentes de acordo com o SLA desejado, utilizamos o seguinte framework:")

        foto2 = Image.open('Framework_Simulador.png')
        st.image(foto2, caption='Framework do Simulador', use_column_width=False, width=600)

    st.subheader("Parâmetros do modelo:")
    with st.container():
        st.write(
            "Parâmetros básicos do modelo M/M/c:\n1. Demanda de Clientes \n2. Tempo Médio de Atendimento \n 3. '# de Servidores")
        
        foto3 = Image.open('FILA.png')
        st.image(foto3, caption='Modelo de Fila M/M/c', use_column_width=False, width=500)

    st.subheader("Outputs:")
    with st.container():
        st.write("Com base em 2 SLA de escolha: (1) Tempo Médio e (2) x % de clientes atendidos em até x segundos.")
        st.write("(1) # PDVs Necessários, (2) Tempo Médio de Fila, (3) Tamanho Médio da Fila, (4) % de Clientes que passaram mais de T minutos e (5) Probabilidade Clientes que estarão presentes na fila.")

if selected == "Página Inicial":

    # foto = Image.open('logo_analytics.png')
    # st.image(foto, caption='Squad Analytics', use_column_width=False)

    st.subheader("Seleção do SLA para a Análise")

    sla_tupla = (
        "SLA 1: Tempo Médio de Fila", "SLA 1*: Tempo Médio de Fila",
        "SLA 2: x % de clientes atendidos em até x segundos")

    sla = st.radio("SLA:", sla_tupla)

    st.subheader("Input:")

    if sla == sla_tupla[0]:
        flag = 0  # tempo Médio
    if sla == sla_tupla[1]:
        flag = 1  # tempo médio*
    if sla == sla_tupla[2]:
        flag = 2  # 90% e tempo max

    st.write(
        "Para o input são necessárias as seguintes colunas: (1) Loja, (2) Período, (3) Tipo, (4) # PDVs MAX, (5) # PDVs Atuais, (6) # PDV Teste, (7) Demanda (POR HORA), (8) TMA (EM SEGUNDOS), (9) SLA: TEMPO MÉDIO, (10) SLA %, (11) SLA: TEMPO MAX e (12) # CLIENTES / CAIXA. Como você pode ver no template abaixo:")

    dict = {'Loja': [], 'Período': [], 'Tipo': [], '# de PDVs MAX': [], '# PDVs Atuais': [], '# PDVs TESTE': [],
            'Demanda (POR HORA)': [], 'TMA (EM SEGUNDOS)': [], 'SLA1: TEMPO MÉDIO (SEGUNDOS)': [], ' SLA %': [],
            'SLA: TEMPO MAX ': [],
            'SLA:# de CLIENTES / CAIXA': []}

    st.table(dict)

    st.write(
        "Observação: o input (8) está relacionado ao SLA 1 e SLA 1*, os inputs (9) e (10) estão relacionados ao SLA 2 e o input (11) aos SLA 3 e 3* que ainda serão implementados.")

    st.write("Clique abaixo para baixar o template do input:")

    with open("input_simulador_filas.xlsx", "rb") as file:
        btn = st.download_button(
            label="📥 DOWNLOAD TEMPLATE",
            data=file,
            file_name="input_simulador_filas.xlsx"
        )

    simulador_frente_caixa = st.file_uploader('Insira a planilha de input')

    if simulador_frente_caixa:

        st.write("Input dos dados:")
        Input_Simulador_Filas = pd.read_excel(simulador_frente_caixa)

        st.dataframe(Input_Simulador_Filas)
        colunas = Input_Simulador_Filas.columns

        # Salvando informações:
        Loja = list(Input_Simulador_Filas[colunas[0]])
        Periodo = list(Input_Simulador_Filas[colunas[1]])
        Tipo = list(Input_Simulador_Filas[colunas[2]])
        Hora = list(Input_Simulador_Filas[colunas[3]])
        DEMANDA = list(Input_Simulador_Filas[colunas[4]])
        TMA = list(Input_Simulador_Filas[colunas[5]])
        PDV_ATUAIS = list(Input_Simulador_Filas[colunas[6]])
        PDV_MAX = list(Input_Simulador_Filas[colunas[7]])
        PDV_TESTE = list(Input_Simulador_Filas[colunas[8]])
        SLA_TEMPO = list(Input_Simulador_Filas[colunas[9]])
        SLA_PER_ = list(Input_Simulador_Filas[colunas[10]])
        SLA_TEMPO_MAX_ = list(Input_Simulador_Filas[colunas[11]])
        SLA_CLIENTE_CAIXA_ = list(Input_Simulador_Filas[colunas[12]])

        # 1. ESTADO ATUAL:
        # Listas:

        Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []

        PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []

        PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []

        MUDANCA = []
        CAPACITY = []
        for i in range(len(DEMANDA)):

            # Parâmetros Primordiais:
            arrival_rate = DEMANDA[i]
            departure_rate = 1 / (TMA[i] / 3600)
            capacity = PDV_ATUAIS[i]
            capacity_antiga = capacity
            # Guarda SLA:
            SLA_TEMPO_MEDIO = SLA_TEMPO[i]
            SLA_TEMPO_MAX = SLA_TEMPO_MAX_[i]
            SLA_PER = SLA_PER_[i]
            SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[i]

            # 1. Parâmetros Atuais
            while (arrival_rate / (departure_rate * capacity)) >= 1:
                capacity = capacity + 1

            fila = MMcQueue(arrival_rate, departure_rate, capacity)
            tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = queue_outputs(
                fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
            # PROB_LIST

            PROB_QTD0, PROB_QTD1, PROB_QTD2, PROB_QTD3, PROB_QTD4, PROB_QTD5, PROB_QTD6, PROB_QTD7, PROB_QTD8, PROB_QTD9, PROB_QTD10, PROB_QTD11 = \
                prob_qtd_pessoas_list[0], prob_qtd_pessoas_list[1], prob_qtd_pessoas_list[2], prob_qtd_pessoas_list[3], \
                prob_qtd_pessoas_list[4], prob_qtd_pessoas_list[5], prob_qtd_pessoas_list[6], prob_qtd_pessoas_list[7], \
                prob_qtd_pessoas_list[8], prob_qtd_pessoas_list[9], prob_qtd_pessoas_list[10], prob_qtd_pessoas_list[11]

            # PROB_TIME
            PROB_TIME1, PROB_TIME2, PROB_TIME3, PROB_TIME4, PROB_TIME5 = prob_time_list[0], prob_time_list[1], \
                                                                         prob_time_list[2], prob_time_list[3], \
                                                                         prob_time_list[4]

            # APPEND:
            Tempo_Medio.append(tempo_medio)
            Tempo_Medio_asterisco.append(tempo_medio)
            PROB_Tempo_Medio.append(prob_pessoas_MED)
            PROB_Tempo_MAX.append(prob_pessoas_MAX)
            TAMANHO_MEDIO.append(tamanho)
            TAMANHO_POR_PDV.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
            PROB_TIME1_.append(PROB_TIME1)
            PROB_TIME2_.append(PROB_TIME2)
            PROB_TIME3_.append(PROB_TIME3)
            PROB_TIME4_.append(PROB_TIME4)
            PROB_TIME5_.append(PROB_TIME5)
            PROB_QTD0_.append(PROB_QTD0)
            PROB_QTD1_.append(PROB_QTD1)
            PROB_QTD2_.append(PROB_QTD2)
            PROB_QTD3_.append(PROB_QTD3)
            PROB_QTD4_.append(PROB_QTD4)
            PROB_QTD5_.append(PROB_QTD5)
            PROB_QTD6_.append(PROB_QTD6)
            PROB_QTD7_.append(PROB_QTD7)
            PROB_QTD8_.append(PROB_QTD8)
            PROB_QTD9_.append(PROB_QTD9)
            PROB_QTD10_.append(PROB_QTD10)
            PROB_QTD11_.append(PROB_QTD11)

            if capacity != capacity_antiga:
                a = "INSTÁVEL"
            else:
                a = "ESTÁVEL"
            MUDANCA.append(a)

            CAPACITY.append(capacity)

        ## (1) Resultado para estado Atual:
        dict_1 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV ATUAIS": PDV_ATUAIS,
                  "PDV Necessário": CAPACITY, "DEMANDA": DEMANDA,
                  "TMA": TMA, 'MUDANCA': MUDANCA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                  "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                  "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                  "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_, "PROB_T4": PROB_TIME4_,
                  "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_, 'PROB_QTD2_': PROB_QTD2_,
                  "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_, 'PROB_QTD5_': PROB_QTD5_,
                  'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_, 'PROB_QTD8_': PROB_QTD8_,
                  'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_, 'PROB_QTD11_': PROB_QTD11_}

        # 2. Parâmetros no Máximo
        # Listas:
        # Listas:

        Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []

        PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []

        PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []

        MUDANCA = []

        CAPACITY = []

        for i in range(len(DEMANDA)):
            # Parâmetros Primordiais:
            arrival_rate = DEMANDA[i]
            departure_rate = 1 / (TMA[i] / 3600)
            capacity = PDV_MAX[i]
            capacity_antiga = capacity
            # Guarda SLA:
            SLA_TEMPO_MEDIO = SLA_TEMPO[i]
            SLA_TEMPO_MAX = SLA_TEMPO_MAX_[i]
            SLA_PER = SLA_PER_[i]
            SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[i]

            # 1. Parâmetros Atuais
            while (arrival_rate / (departure_rate * capacity)) >= 1:
                capacity = capacity + 1

            fila = MMcQueue(arrival_rate, departure_rate, capacity)
            tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = queue_outputs(
                fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
            # PROB_LIST
            PROB_QTD0 = prob_qtd_pessoas_list[0]
            PROB_QTD1 = prob_qtd_pessoas_list[1]
            PROB_QTD2 = prob_qtd_pessoas_list[2]
            PROB_QTD3 = prob_qtd_pessoas_list[3]
            PROB_QTD4 = prob_qtd_pessoas_list[4]
            PROB_QTD5 = prob_qtd_pessoas_list[5]
            PROB_QTD6 = prob_qtd_pessoas_list[6]
            PROB_QTD7 = prob_qtd_pessoas_list[7]
            PROB_QTD8 = prob_qtd_pessoas_list[8]
            PROB_QTD9 = prob_qtd_pessoas_list[9]
            PROB_QTD10 = prob_qtd_pessoas_list[10]
            PROB_QTD11 = prob_qtd_pessoas_list[11]
            # PROB_TIME
            PROB_TIME1 = prob_time_list[0]
            PROB_TIME2 = prob_time_list[1]
            PROB_TIME3 = prob_time_list[2]
            PROB_TIME4 = prob_time_list[3]
            PROB_TIME5 = prob_time_list[4]

            # APPEND:
            Tempo_Medio.append(tempo_medio * 3600)
            Tempo_Medio_asterisco.append(tempo_medio_asterisco * 3600)
            PROB_Tempo_Medio.append(prob_pessoas_MED)
            PROB_Tempo_MAX.append(prob_pessoas_MAX)
            TAMANHO_MEDIO.append(tamanho)
            TAMANHO_POR_PDV.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
            PROB_TIME1_.append(PROB_TIME1)
            PROB_TIME2_.append(PROB_TIME2)
            PROB_TIME3_.append(PROB_TIME3)
            PROB_TIME4_.append(PROB_TIME4)
            PROB_TIME5_.append(PROB_TIME5)
            PROB_QTD0_.append(PROB_QTD0)
            PROB_QTD1_.append(PROB_QTD1)
            PROB_QTD2_.append(PROB_QTD2)
            PROB_QTD3_.append(PROB_QTD3)
            PROB_QTD4_.append(PROB_QTD4)
            PROB_QTD5_.append(PROB_QTD5)
            PROB_QTD6_.append(PROB_QTD6)
            PROB_QTD7_.append(PROB_QTD7)
            PROB_QTD8_.append(PROB_QTD8)
            PROB_QTD9_.append(PROB_QTD9)
            PROB_QTD10_.append(PROB_QTD10)
            PROB_QTD11_.append(PROB_QTD11)

            CAPACITY.append(capacity)

            if capacity != capacity_antiga:
                a = "INSTÁVEL"
            else:
                a = "ESTÁVEL"
            MUDANCA.append(a)

        ## (1) Resultado para estado Atual:
        dict_2 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV MAX": PDV_MAX,
                  "PDV Necessário": CAPACITY, "DEMANDA": DEMANDA,
                  "TMA": TMA, 'MUDANCA': MUDANCA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                  "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                  "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                  "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_, "PROB_T4": PROB_TIME4_,
                  "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_, 'PROB_QTD2_': PROB_QTD2_,
                  "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_, 'PROB_QTD5_': PROB_QTD5_,
                  'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_, 'PROB_QTD8_': PROB_QTD8_,
                  'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_, 'PROB_QTD11_': PROB_QTD11_}

        # 3. Testar com os HC que eu quero:

        # Listas:

        Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []

        PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []

        PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []

        CAPACITY = []

        MUDANCA = []

        for i in range(len(DEMANDA)):
            # Parâmetros Primordiais:
            arrival_rate = DEMANDA[i]
            departure_rate = 1 / (TMA[i] / 3600)
            capacity = PDV_TESTE[i]
            capacity_antiga = capacity
            # Guarda SLA:
            SLA_TEMPO_MEDIO = SLA_TEMPO[i]
            SLA_TEMPO_MAX = SLA_TEMPO_MAX_[i]
            SLA_PER = SLA_PER_[i]
            SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[i]

            # 1. Parâmetros Atuais
            while (arrival_rate / (departure_rate * capacity)) >= 1:
                capacity = capacity + 1

            fila = MMcQueue(arrival_rate, departure_rate, capacity)
            tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = queue_outputs(
                fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
            # PROB_LIST
            PROB_QTD0 = prob_qtd_pessoas_list[0]
            PROB_QTD1 = prob_qtd_pessoas_list[1]
            PROB_QTD2 = prob_qtd_pessoas_list[2]
            PROB_QTD3 = prob_qtd_pessoas_list[3]
            PROB_QTD4 = prob_qtd_pessoas_list[4]
            PROB_QTD5 = prob_qtd_pessoas_list[5]
            PROB_QTD6 = prob_qtd_pessoas_list[6]
            PROB_QTD7 = prob_qtd_pessoas_list[7]
            PROB_QTD8 = prob_qtd_pessoas_list[8]
            PROB_QTD9 = prob_qtd_pessoas_list[9]
            PROB_QTD10 = prob_qtd_pessoas_list[10]
            PROB_QTD11 = prob_qtd_pessoas_list[11]

            # PROB_TIME
            PROB_TIME1 = prob_time_list[0]
            PROB_TIME2 = prob_time_list[1]
            PROB_TIME3 = prob_time_list[2]
            PROB_TIME4 = prob_time_list[3]
            PROB_TIME5 = prob_time_list[4]

            # APPEND:
            Tempo_Medio.append(tempo_medio * 3600)
            Tempo_Medio_asterisco.append(tempo_medio_asterisco * 3600)
            PROB_Tempo_Medio.append(prob_pessoas_MED)
            PROB_Tempo_MAX.append(prob_pessoas_MAX)
            TAMANHO_MEDIO.append(tamanho)
            TAMANHO_POR_PDV.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO.append(tamanho_por_pdv)
            TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
            PROB_TIME1_.append(PROB_TIME1)
            PROB_TIME2_.append(PROB_TIME2)
            PROB_TIME3_.append(PROB_TIME3)
            PROB_TIME4_.append(PROB_TIME4)
            PROB_TIME5_.append(PROB_TIME5)
            PROB_QTD0_.append(PROB_QTD0)
            PROB_QTD1_.append(PROB_QTD1)
            PROB_QTD2_.append(PROB_QTD2)
            PROB_QTD3_.append(PROB_QTD3)
            PROB_QTD4_.append(PROB_QTD4)
            PROB_QTD5_.append(PROB_QTD5)
            PROB_QTD6_.append(PROB_QTD6)
            PROB_QTD7_.append(PROB_QTD7)
            PROB_QTD8_.append(PROB_QTD8)
            PROB_QTD9_.append(PROB_QTD9)
            PROB_QTD10_.append(PROB_QTD10)
            PROB_QTD11_.append(PROB_QTD11)

            if capacity != capacity_antiga:
                a = "INSTÁVEL"
            else:
                a = "ESTÁVEL"
            MUDANCA.append(a)

            CAPACITY.append(capacity)

        ## (1) Resultado para estado Atual:

        dict_3 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV TESTE": PDV_TESTE,
                  "PDV NECESSÀRIO": CAPACITY, "DEMANDA": DEMANDA,
                  "TMA": TMA, 'MUDANCA': MUDANCA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                  "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                  "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                  "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_, "PROB_T4": PROB_TIME4_,
                  "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_, 'PROB_QTD2_': PROB_QTD2_,
                  "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_, 'PROB_QTD5_': PROB_QTD5_,
                  'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_, 'PROB_QTD8_': PROB_QTD8_,
                  'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_, 'PROB_QTD11_': PROB_QTD11_}

        # Otimização:

        if flag == 0:
            # Listas:
            Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []
            PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []
            PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []
            MUDANCA = []
            CAPACITY = []

            for j in range(len(DEMANDA)):
                # Parâmetros Primordiais:
                arrival_rate = DEMANDA[j]
                departure_rate = 1 / (TMA[j] / 3600)
                capacity = PDV_ATUAIS[j]
                capacity_antiga = capacity
                # Guarda SLA:
                SLA_TEMPO_MEDIO = SLA_TEMPO[j] / 3600
                SLA_TEMPO_MAX = SLA_TEMPO_MAX_[j] / 3600
                SLA_PER = SLA_PER_[j]
                SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[j]

                while (arrival_rate / (departure_rate * capacity)) >= 1:
                    capacity = capacity + 1

                fila = MMcQueue(arrival_rate, departure_rate, capacity)
                tempo_medio = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[0]
                tempo_medio_asterisco = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[1]

                metrica = tempo_medio
                resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                while metrica > SLA_TEMPO_MEDIO:
                    capacity = capacity + 1

                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    tempo_medio = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[0]
                    metrica = tempo_medio
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                    st.write(metrica, SLA_TEMPO_MEDIO)

                while metrica <= SLA_TEMPO_MEDIO:

                    metrica_2 = metrica
                    resultado_2 = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
                    capacity = capacity - 1
                    if (arrival_rate / (departure_rate * capacity)) >= 1:
                        capacity = capacity + 1
                        break
                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                    metrica = resultado[0]

                DIFF_1 = metrica - SLA_TEMPO_MEDIO
                DIFF_2 = metrica_2 - SLA_TEMPO_MEDIO

                if abs(DIFF_1) <= abs(DIFF_2):
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado
                else:
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado_2

                    # PROB_LIST
                PROB_QTD0 = prob_qtd_pessoas_list[0]
                PROB_QTD1 = prob_qtd_pessoas_list[1]
                PROB_QTD2 = prob_qtd_pessoas_list[2]
                PROB_QTD3 = prob_qtd_pessoas_list[3]
                PROB_QTD4 = prob_qtd_pessoas_list[4]
                PROB_QTD5 = prob_qtd_pessoas_list[5]
                PROB_QTD6 = prob_qtd_pessoas_list[6]
                PROB_QTD7 = prob_qtd_pessoas_list[7]
                PROB_QTD8 = prob_qtd_pessoas_list[8]
                PROB_QTD9 = prob_qtd_pessoas_list[9]
                PROB_QTD10 = prob_qtd_pessoas_list[10]
                PROB_QTD11 = prob_qtd_pessoas_list[11]
                # PROB_TIME
                PROB_TIME1 = prob_time_list[0]
                PROB_TIME2 = prob_time_list[1]
                PROB_TIME3 = prob_time_list[2]
                PROB_TIME4 = prob_time_list[3]
                PROB_TIME5 = prob_time_list[4]

                # APPEND:
                Tempo_Medio.append(tempo_medio * 3600)
                Tempo_Medio_asterisco.append(tempo_medio_asterisco * 3600)
                PROB_Tempo_Medio.append(prob_pessoas_MED)
                PROB_Tempo_MAX.append(prob_pessoas_MAX)
                TAMANHO_MEDIO.append(tamanho)
                TAMANHO_POR_PDV.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
                PROB_TIME1_.append(PROB_TIME1)
                PROB_TIME2_.append(PROB_TIME2)
                PROB_TIME3_.append(PROB_TIME3)
                PROB_TIME4_.append(PROB_TIME4)
                PROB_TIME5_.append(PROB_TIME5)
                PROB_QTD0_.append(PROB_QTD0)
                PROB_QTD1_.append(PROB_QTD1)
                PROB_QTD2_.append(PROB_QTD2)
                PROB_QTD3_.append(PROB_QTD3)
                PROB_QTD4_.append(PROB_QTD4)
                PROB_QTD5_.append(PROB_QTD5)
                PROB_QTD6_.append(PROB_QTD6)
                PROB_QTD7_.append(PROB_QTD7)
                PROB_QTD8_.append(PROB_QTD8)
                PROB_QTD9_.append(PROB_QTD9)
                PROB_QTD10_.append(PROB_QTD10)
                PROB_QTD11_.append(PROB_QTD11)
                CAPACITY.append(capacity)

            dict_4 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV ATUAIS": PDV_ATUAIS,
                      "PDV Necessário": CAPACITY, "DEMANDA": DEMANDA,
                      "TMA": TMA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                      "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                      "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                      "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_,
                      "PROB_T4": PROB_TIME4_,
                      "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_,
                      'PROB_QTD2_': PROB_QTD2_, "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_,
                      'PROB_QTD5_': PROB_QTD5_, 'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_,
                      'PROB_QTD8_': PROB_QTD8_, 'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_,
                      'PROB_QTD11_': PROB_QTD11_}

        if flag == 1:
            # Listas:
            Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []
            PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []
            PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []
            MUDANCA = []
            CAPACITY = []

            for j in range(len(DEMANDA)):
                # Parâmetros Primordiais:
                arrival_rate = DEMANDA[j]
                departure_rate = 1 / (TMA[j] / 3600)
                capacity = PDV_ATUAIS[j]
                capacity_antiga = capacity
                # Guarda SLA:
                SLA_TEMPO_MEDIO = SLA_TEMPO[j] / 3600
                SLA_TEMPO_MAX = SLA_TEMPO_MAX_[j] / 3600
                SLA_PER = SLA_PER_[j]
                SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[j]

                while (arrival_rate / (departure_rate * capacity)) >= 1:
                    capacity = capacity + 1

                fila = MMcQueue(arrival_rate, departure_rate, capacity)
                tempo_medio = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[0]
                tempo_medio_asterisco = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[1]

                metrica = tempo_medio_asterisco
                resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                while metrica > SLA_TEMPO_MEDIO:
                    capacity = capacity + 1
                    st.write('check1', metrica, SLA_TEMPO_MEDIO)
                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    tempo_medio_asterisco = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[1]
                    metrica = tempo_medio_asterisco
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                while metrica <= SLA_TEMPO_MEDIO:

                    metrica_2 = metrica
                    resultado_2 = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
                    capacity = capacity - 1
                    if (arrival_rate / (departure_rate * capacity)) >= 1:
                        capacity = capacity + 1
                        break

                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                    metrica = resultado[1]

                DIFF_1 = metrica - SLA_TEMPO_MEDIO
                DIFF_2 = metrica_2 - SLA_TEMPO_MEDIO

                if abs(DIFF_1) <= abs(DIFF_2):
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado
                else:
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado_2

                    # PROB_LIST
                PROB_QTD0 = prob_qtd_pessoas_list[0]
                PROB_QTD1 = prob_qtd_pessoas_list[1]
                PROB_QTD2 = prob_qtd_pessoas_list[2]
                PROB_QTD3 = prob_qtd_pessoas_list[3]
                PROB_QTD4 = prob_qtd_pessoas_list[4]
                PROB_QTD5 = prob_qtd_pessoas_list[5]
                PROB_QTD6 = prob_qtd_pessoas_list[6]
                PROB_QTD7 = prob_qtd_pessoas_list[7]
                PROB_QTD8 = prob_qtd_pessoas_list[8]
                PROB_QTD9 = prob_qtd_pessoas_list[9]
                PROB_QTD10 = prob_qtd_pessoas_list[10]
                PROB_QTD11 = prob_qtd_pessoas_list[11]
                # PROB_TIME
                PROB_TIME1 = prob_time_list[0]
                PROB_TIME2 = prob_time_list[1]
                PROB_TIME3 = prob_time_list[2]
                PROB_TIME4 = prob_time_list[3]
                PROB_TIME5 = prob_time_list[4]

                # APPEND:
                Tempo_Medio.append(tempo_medio * 3600)
                Tempo_Medio_asterisco.append(tempo_medio_asterisco * 3600)
                PROB_Tempo_Medio.append(prob_pessoas_MED)
                PROB_Tempo_MAX.append(prob_pessoas_MAX)
                TAMANHO_MEDIO.append(tamanho)
                TAMANHO_POR_PDV.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
                PROB_TIME1_.append(PROB_TIME1)
                PROB_TIME2_.append(PROB_TIME2)
                PROB_TIME3_.append(PROB_TIME3)
                PROB_TIME4_.append(PROB_TIME4)
                PROB_TIME5_.append(PROB_TIME5)
                PROB_QTD0_.append(PROB_QTD0)
                PROB_QTD1_.append(PROB_QTD1)
                PROB_QTD2_.append(PROB_QTD2)
                PROB_QTD3_.append(PROB_QTD3)
                PROB_QTD4_.append(PROB_QTD4)
                PROB_QTD5_.append(PROB_QTD5)
                PROB_QTD6_.append(PROB_QTD6)
                PROB_QTD7_.append(PROB_QTD7)
                PROB_QTD8_.append(PROB_QTD8)
                PROB_QTD9_.append(PROB_QTD9)
                PROB_QTD10_.append(PROB_QTD10)
                PROB_QTD11_.append(PROB_QTD11)
                CAPACITY.append(capacity)

            dict_4 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV ATUAIS": PDV_ATUAIS,
                      "PDV NECESSÀRIOS": CAPACITY, "DEMANDA": DEMANDA,
                      "TMA": TMA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                      "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                      "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                      "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_,
                      "PROB_T4": PROB_TIME4_,
                      "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_,
                      'PROB_QTD2_': PROB_QTD2_, "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_,
                      'PROB_QTD5_': PROB_QTD5_, 'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_,
                      'PROB_QTD8_': PROB_QTD8_, 'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_,
                      'PROB_QTD11_': PROB_QTD11_}

        # % Clientes atendidos em até SLA_PER

        if flag == 2:
            # Listas:
            Tempo_Medio, Tempo_Medio_asterisco, PROB_Tempo_Medio, PROB_Tempo_MAX, TAMANHO_MEDIO, TAMANHO_POR_PDV, TAMANHO_ASTERISCO, TAMANHO_ASTERISCO_PDV = [], [], [], [], [], [], [], []
            PROB_TIME1_, PROB_TIME2_, PROB_TIME3_, PROB_TIME4_, PROB_TIME5_ = [], [], [], [], []
            PROB_QTD0_, PROB_QTD1_, PROB_QTD2_, PROB_QTD3_, PROB_QTD4_, PROB_QTD5_, PROB_QTD6_, PROB_QTD7_, PROB_QTD8_, PROB_QTD9_, PROB_QTD10_, PROB_QTD11_ = [], [], [], [], [], [], [], [], [], [], [], []
            MUDANCA = []
            CAPACITY = []

            for j in range(len(DEMANDA)):
                # Parâmetros Primordiais:
                arrival_rate = DEMANDA[j]
                departure_rate = 1 / (TMA[j] / 3600)
                capacity = PDV_ATUAIS[j]
                capacity_antiga = capacity
                # Guarda SLA:
                SLA_TEMPO_MEDIO = SLA_TEMPO[j] / 3600
                SLA_TEMPO_MAX = SLA_TEMPO_MAX_[j] / 3600
                SLA_PER = SLA_PER_[j]
                SLA_CLIENTE_CAIXA = SLA_CLIENTE_CAIXA_[j]

                while (arrival_rate / (departure_rate * capacity)) >= 1:
                    capacity = capacity + 1

                fila = MMcQueue(arrival_rate, departure_rate, capacity)

                PER = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[3]

                metrica = PER
                resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                # SLA_TEMPO_MAX = SLA_TEMPO_MAX[j]
                # SLA_PER = SLA_PER[j]

                while metrica < SLA_PER:
                    capacity = capacity + 1

                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    PER = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)[3]
                    metrica = PER
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                while metrica >= SLA_PER:
                    metrica_2 = metrica
                    resultado_2 = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)
                    capacity = capacity - 1

                    if (arrival_rate / (departure_rate * capacity)) >= 1:
                        capacity = capacity + 1
                        break

                    fila = MMcQueue(arrival_rate, departure_rate, capacity)
                    resultado = queue_outputs(fila, SLA_TEMPO_MEDIO, SLA_TEMPO_MAX, SLA_CLIENTE_CAIXA)

                    metrica = resultado[1]

                DIFF_1 = metrica - SLA_TEMPO_MEDIO
                DIFF_2 = metrica_2 - SLA_TEMPO_MEDIO

                if abs(DIFF_1) <= abs(DIFF_2):
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado
                else:
                    tempo_medio, tempo_medio_asterisco, prob_pessoas_MED, prob_pessoas_MAX, tamanho, tamanho_por_pdv, tamanho_asterisco, tamanho_asterisco_pdv, prob_qtd_pessoas_list, prob_time_list = resultado_2

                    # PROB_LIST
                PROB_QTD0 = prob_qtd_pessoas_list[0]
                PROB_QTD1 = prob_qtd_pessoas_list[1]
                PROB_QTD2 = prob_qtd_pessoas_list[2]
                PROB_QTD3 = prob_qtd_pessoas_list[3]
                PROB_QTD4 = prob_qtd_pessoas_list[4]
                PROB_QTD5 = prob_qtd_pessoas_list[5]
                PROB_QTD6 = prob_qtd_pessoas_list[6]
                PROB_QTD7 = prob_qtd_pessoas_list[7]
                PROB_QTD8 = prob_qtd_pessoas_list[8]
                PROB_QTD9 = prob_qtd_pessoas_list[9]
                PROB_QTD10 = prob_qtd_pessoas_list[10]
                PROB_QTD11 = prob_qtd_pessoas_list[11]
                # PROB_TIME
                PROB_TIME1 = prob_time_list[0]
                PROB_TIME2 = prob_time_list[1]
                PROB_TIME3 = prob_time_list[2]
                PROB_TIME4 = prob_time_list[3]
                PROB_TIME5 = prob_time_list[4]

                # APPEND:
                Tempo_Medio.append(tempo_medio)
                Tempo_Medio_asterisco.append(tempo_medio_asterisco)
                PROB_Tempo_Medio.append(prob_pessoas_MED)
                PROB_Tempo_MAX.append(prob_pessoas_MAX)
                TAMANHO_MEDIO.append(tamanho)
                TAMANHO_POR_PDV.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO.append(tamanho_por_pdv)
                TAMANHO_ASTERISCO_PDV.append(tamanho_asterisco_pdv)
                PROB_TIME1_.append(PROB_TIME1)
                PROB_TIME2_.append(PROB_TIME2)
                PROB_TIME3_.append(PROB_TIME3)
                PROB_TIME4_.append(PROB_TIME4)
                PROB_TIME5_.append(PROB_TIME5)
                PROB_QTD0_.append(PROB_QTD0)
                PROB_QTD1_.append(PROB_QTD1)
                PROB_QTD2_.append(PROB_QTD2)
                PROB_QTD3_.append(PROB_QTD3)
                PROB_QTD4_.append(PROB_QTD4)
                PROB_QTD5_.append(PROB_QTD5)
                PROB_QTD6_.append(PROB_QTD6)
                PROB_QTD7_.append(PROB_QTD7)
                PROB_QTD8_.append(PROB_QTD8)
                PROB_QTD9_.append(PROB_QTD9)
                PROB_QTD10_.append(PROB_QTD10)
                PROB_QTD11_.append(PROB_QTD11)

                CAPACITY.append(capacity)

            dict_4 = {"Loja": Loja, "Periodo": Periodo, "Tipo": Tipo, "Hora": Hora, "PDV ATUAIS": PDV_ATUAIS,
                      "PDV NECESSÁRIOS": CAPACITY, "DEMANDA": DEMANDA,
                      "TMA": TMA, "Tempo Médio": Tempo_Medio, "Tempo Médio *": Tempo_Medio_asterisco,
                      "Prob(T<= Tempo Médio)": PROB_Tempo_Medio, "Prob(T<= Tempo Max)": PROB_Tempo_MAX,
                      "Clientes por PDV": TAMANHO_POR_PDV, "Clientes por PDV *": TAMANHO_ASTERISCO_PDV,
                      "PROB_T1": PROB_TIME1_, "PROB_T2": PROB_TIME2_, "PROB_T3": PROB_TIME3_,
                      "PROB_T4": PROB_TIME4_,
                      "PROB_T5": PROB_TIME5_, "PROB_QTD0_": PROB_QTD0_, "PROB_QTD1_": PROB_QTD1_,
                      'PROB_QTD2_': PROB_QTD2_, "PROB_QTD3_": PROB_QTD3_, 'PROB_QTD4_': PROB_QTD4_,
                      'PROB_QTD5_': PROB_QTD5_, 'PROB_QTD6_': PROB_QTD6_, 'PROB_QTD7_': PROB_QTD7_,
                      'PROB_QTD8_': PROB_QTD8_, 'PROB_QTD9_': PROB_QTD9_, 'PROB_QTD10_': PROB_QTD10_,
                      'PROB_QTD11_': PROB_QTD11_}

        # DICT 1: ATUAL
        # DICT 2: MAX
        # DICT 3: EU QUERO
        # DICT 4: FLAG 0: TEMPO MED, FLAG 1: TEMPO MAX, FLAG 2: TEMPO
        df1 = pd.DataFrame(dict_1)
        df2 = pd.DataFrame(dict_2)
        df3 = pd.DataFrame(dict_3)
        df4 = pd.DataFrame(dict_4)

        st.subheader("Output Descritivo:")

        # ATUAL:
        st.write("PDV ATUAL")
        st.table(dict_1)
        # selection1 = aggrid_interactive_table(df=df1)

        # MAX:
        st.write("PDV MAX:")
        st.table(dict_2)
        # selection2 = aggrid_interactive_table(df=df2)

        # QUERO:
        st.write("PDV TESTE:")
        st.table(dict_3)
        # selection3 = aggrid_interactive_table(df=df3)

        # DESEJADO:
        st.subheader("Output Otimizado:")

        if flag == 0:
            st.write(sla_tupla[0])
        if flag == 1:
            st.write(sla_tupla[1])
        if flag == 2:
            st.write(sla_tupla[2])

        st.table(dict_4)


        # selection4 = aggrid_interactive_table(df=dict_4)


        def to_excel(df,df1,df2,df3,df4):
                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                df.to_excel(writer, index=False, sheet_name='Input')
                df1.to_excel(writer, index=False, sheet_name='PDV ATUAL')
                df2.to_excel(writer, index= False, sheet_name = 'PDV MAX')
                df3.to_excel(writer, index=False, sheet_name='PDV TESTE')
                df4.to_excel(writer, index=False, sheet_name='PDV OTIMIZADO '+ str(flag) )


                workbook = writer.book

                worksheet = writer.sheets['Input']
                worksheet1 = writer.sheets['PDV ATUAL']
                worksheet2 = writer.sheets['PDV MAX']
                worksheet3 = writer.sheets['PDV TESTE']

                worksheet4 = writer.sheets['PDV OTIMIZADO '+ str(flag)]
                format1 = workbook.add_format({'num_format': '0.00'})

                worksheet.set_column('B:B', None, format1)
                worksheet1.set_column('B:B', None, format1)
                worksheet2.set_column('B:B', None, format1)
                worksheet3.set_column('B:B', None, format1)
                worksheet4.set_column('B:B', None, format1)

                writer.save()
                processed_data = output.getvalue()
                return processed_data


        df_xlsx = to_excel(Input_Simulador_Filas, df1, df2, df3, df4)

        st.download_button(label='📥 Clique aqui para baixar os resultados',
                           data=df_xlsx,
                           file_name='Simulador_Caixas.xlsx')

