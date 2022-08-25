import pandas as pd
import streamlit as st
import numpy as np
import math
from PIL import Image
from io import BytesIO
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

#   3. Number of Servers:   `capacity`
st.title('Pragmatis Consultoria - Squad Analytics')

st.header("Simulador de Frente de Caixas")
foto = Image.open('logo_analytics.png')
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

st.image(foto, caption='Squad Analytics', use_column_width=False)

st.write("Esse simulador é construído com base em Teoria das Filas e utiliza o modelo M/M/C que considera algumas premissas: (1) Tempo entre Chegadas e Tempos de atendimento seguem uma distribuição exponencial\n, (2) Todos os clientes são considerados como uma fila única com múltiplos\n(3) Os tempos de atendimento para cada caixa tem igual produtividade.\n Para mais informações, consultar: https://pt.wikipedia.org/wiki/Teoria_das_filas e https://pt.wikipedia.org/wiki/Fila_M/M/1\n")

st.write("O input para o simulador deve seguir a seguinte ordem nas colunas (1) Código da Loja, (2) Dia da Semana, (3) Período (horário), (4) Taxa de Chegada de Cliente nos Caixas, (5) Taxa de Atendimento por PDV, (6) # de PDVs Ativos, SLA (Tempo médio de espera na fila)\n")

st.write("Observação: caso não tenha a informação dos PDVs ativos preencher com um valor condizente.")

st.subheader("Input")
simulador_frente_caixa = st.file_uploader('Insira a planilha de input')

if simulador_frente_caixa:
    
    Input_Simulador_Filas = pd.read_excel(simulador_frente_caixa)
    st.dataframe(Input_Simulador_Filas)
    colunas = Input_Simulador_Filas.columns

    # Salvando informações:
    TA = Input_Simulador_Filas[colunas[3]]
    TC = Input_Simulador_Filas[colunas[4]]
    TE = list(Input_Simulador_Filas[colunas[5]])
    PDVA = list(Input_Simulador_Filas[colunas[6]])
    SLA_ = list(Input_Simulador_Filas[colunas[6]])

    # Criando listas para preencher os dados:
    TF = []
    TFG = []
    TAM = []
    TAMG = []
    PDV = []

    for i in range(len(TA)):

      arrival_rate = TC[i]
      departure_rate = TA[i]
      capacity = PDVA[i]
      SLA = SLA_[i]

      Fila = MMcQueue(arrival_rate,departure_rate,capacity)

      PO = round(Fila.getIdleProb(),4) # Probabilidade de Estar Vazia
      Tempo_de_Fila = round(Fila.getAvgQueueTime_Given(),4) # Tempo de Fila
      PROB_SLA = round(Fila.getPorbWhenQueueTimeLargerThan(SLA),4)
      Tamanho = round(Fila.getAvgPackets(),4)
      Tamanho_Given =  round(Fila.getAvgQueuePacket_Given(),4)
      Tempo = round(Fila.getAvgQueueTime(),4)
      Tempo_Given =round(Fila.getAvgQueueTime_Given(),4)

      if Tempo_Given<SLA:

        while (Tempo_Given > SLA):
          capacity = capacity + 1
          Fila = MMcQueue(arrival_rate,departure_rate,capacity)
          PO = round(Fila.getIdleProb(),4) # Probabilidade de Estar Vazia
          Tempo_de_Fila = round(Fila.getAvgQueueTime_Given(),4) # Tempo de Fila
          PROB_SLA = round(Fila.getPorbWhenQueueTimeLargerThan(SLA),4)
          Tamanho = round(Fila.getAvgPackets(),4)
          Tamanho_Given =  round(Fila.getAvgQueuePacket_Given(),4)
          Tempo = round(Fila.getAvgQueueTime(),4)
          Tempo_Given =round(Fila.getAvgQueueTime_Given(),4)

      else:

        while(Tempo_Given > SLA*1.30):
          capacity = capacity -1
          Fila = MMcQueue(arrival_rate,departure_rate,capacity)
          PO = round(Fila.getIdleProb(),4) # Probabilidade de Estar Vazia
          Tempo_de_Fila = round(Fila.getAvgQueueTime_Given(),4) # Tempo de Fila
          PROB_SLA = round(Fila.getPorbWhenQueueTimeLargerThan(SLA),4)
          Tamanho = round(Fila.getAvgPackets(),4)
          Tamanho_Given =  round(Fila.getAvgQueuePacket_Given(),4)
          Tempo = round(Fila.getAvgQueueTime(),4)
          Tempo_Given =round(Fila.getAvgQueueTime_Given(),4)

      TF.append(Tempo)
      TFG.append(Tempo_Given)
      TAM.append(Tamanho)
      TAMG.append(Tamanho_Given)
      PDV.append(capacity)
    
    Input_Simulador_Filas["Tempo Médio de Fila"] = TF
    Input_Simulador_Filas["Tempo Médio dado que a Fila Existe"] = TFG
    Input_Simulador_Filas["Tamanho Médio da Fila"] = TAM
    Input_Simulador_Filas["Tamanho Médio da Fila dado que ela existe"] = TAMG
    Input_Simulador_Filas["PDVs necessários"] = PDV
    
    st.subheader("Output")
    st.dataframe(Input_Simulador_Filas, width=20, height=90)
   
    def to_excel(df):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        format1 = workbook.add_format({'num_format': '0.00'})
        worksheet.set_column('A:A', None, format1)
        writer.save()
        processed_data = output.getvalue()
        return processed_data

    df_xlsx = to_excel(Input_Simulador_Filas)

    st.download_button(label='📥 Clique aqui para baixar os resultados',
                       data=df_xlsx,
                       file_name='Simulador_Caixas.xlsx')
