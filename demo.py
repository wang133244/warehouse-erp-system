import torch
import torch.nn as nn
import torch.nn.functional as F
import math
 
# 不带可训练权重的
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        # 初始化位置编码矩阵，(max_len, d_model),默认元素为0
        self.encoding = torch.zeros(max_len, d_model)
        # 生成位置信息，(5000, 1)，元素为0-4999。
        position = torch.arange(0, max_len).unsqueeze(1).float()
 
        # 利用正余弦函数生成位置编码矩阵
        # d_model=8,div_term是[0/8, 2/8, 4/8, 6/8] = 0.0, 0.25, 0.5, 0.75
        div_term = torch.arange(0, d_model, 2).float() / d_model
        # 正弦值给到位置编码张量的偶数索引
        self.encoding[:, 0::2] = torch.sin(position / torch.pow(10000.0, div_term))
        # 余弦值给到位置编码张量的奇数索引
        self.encoding[:, 1::2] = torch.cos(position / torch.pow(10000.0, div_term))
        # 将位置编码拓展bs->(1, max_len, d_model)
        self.encoding = self.encoding.unsqueeze(0)
 
    def forward(self, x):
        # x -> (bs, seq_len, d_model)
        # self.encoding->(1, 5000, d_model)
        x = x + self.encoding[:, :x.size(1)]
        return x
 
class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads):
        super(MultiHeadAttention, self).__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        # 计算每个注意力头的维度
        self.head_dim = self.d_model // self.n_heads
        # Q K V 的 Linear层
        self.WQ = nn.Linear(d_model, d_model)
        self.WK = nn.Linear(d_model, d_model)
        self.WV = nn.Linear(d_model, d_model)
        # 注意力机制输出后的线性变换
        self.fc_out = nn.Linear(d_model, d_model)
 
    def forward(self, query, key, value, mask=None):
        # mask在输入时，encoder是padding mask, 但是decoder输入时：有padding,自回归两个mask
        batch_size = query.size(0)
        # qkv的linear
        Q = self.WQ(query)
        K = self.WK(key)
        V = self.WV(value)
        # 多头的拆分和转置, 512拆成8x64
        Q = Q.view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, -1, self.n_heads, self.head_dim).transpose(1, 2)
        # 缩放点积注意力机制的计算， 注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.head_dim)
 
        if mask is not None:
            scores = scores.masked_fill(mask==0, float("-1e20"))
        weights = F.softmax(scores, dim=-1)
        # 将注意力权重应用到v上
        attention = torch.matmul(weights, V)
        attention = attention.transpose(1, 2).contiguous().view(batch_size, -1, self.d_model)
        output = self.fc_out(attention)
        return output
 
# 定义位置前馈神经网络
class PositionwiseFeedForward(nn.Module):
    def __init__(self, d_model, d_ff):
        super(PositionwiseFeedForward, self).__init__()
        # 定义第一个全连接层
        self.fc1 = nn.Linear(d_model, d_ff)
        # 定义第二个全连接层
        self.fc2 = nn.Linear(d_ff, d_model)
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x
 
# 定义transformer编码器层
class TransformerEncoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff):
        super(TransformerEncoderLayer, self).__init__()
        self.multi_head_attention = MultiHeadAttention(d_model, n_heads)
        self.dropout = nn.Dropout(0.1)
        # 定义第一个LN层
        self.norm1 = nn.LayerNorm(d_model)
        # 定义第二个LN层
        self.norm2 = nn.LayerNorm(d_model)
 
        self.feedforward = PositionwiseFeedForward(d_model, d_ff)
 
    def forward(self, x, mask=None):
        attention_out = self.multi_head_attention(x, x, x, mask)
        x = x + self.dropout(attention_out)
        x = self.norm1(x)
        x = x + self.feedforward(x)
        x = self.norm2(x)
        return x
 
class TransformerEncoder(nn.Module):
    def __init__(self, d_model, n_heads, n_layers, d_ff, input_vocab_size):
        super(TransformerEncoder, self).__init__()
        self.embedding = nn.Embedding(input_vocab_size, d_model)
        self.positional_encoding = PositionalEncoding(d_model)
        self.transformer_layer = nn.ModuleList([TransformerEncoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)])
 
    def forward(self, x, mask=None):
        x = self.embedding(x)
        x = self.positional_encoding(x)
        for layer in self.transformer_layer:
            x = layer(x, mask)
        return x
 
class TransformerDecoderLayer(nn.Module):
    def __init__(self, d_model, n_heads, d_ff):
        super(TransformerDecoderLayer, self).__init__()
        self.multi_head_attention = MultiHeadAttention(d_model, n_heads)
        self.dropout = nn.Dropout(0.1)
        self.norm1 = nn.LayerNorm(d_model)
 
        self.encoder_attention = MultiHeadAttention(d_model, n_heads)
        self.norm2 = nn.LayerNorm(d_model)
 
        self.feedforward = PositionwiseFeedForward(d_model, d_ff)
        self.norm3 = nn.LayerNorm(d_model)
 
    def forward(self, x, encoder_output, src_mask=None, trg_mask=None):
        multi_head_attention_out = self.multi_head_attention(x, x, x, mask=trg_mask)
        x = x + self.dropout(multi_head_attention_out)
        x = self.norm1(x)
 
        encoder_attention_out = self.encoder_attention(x, encoder_output, encoder_output, mask=src_mask)
        x = x + self.dropout(encoder_attention_out)
        x = self.norm2(x)
 
        x = x + self.feedforward(x)
        x = self.norm3(x)
        return x
 
class TransformerDecoder(nn.Module):
    def __init__(self, d_model, n_heads, n_layers, d_ff, output_vocab_size):
        super(TransformerDecoder, self).__init__()
        self.embedding = nn.Embedding(output_vocab_size, d_model)
        self.positonal_encoding = PositionalEncoding(d_model)
        self.decoder_layers = nn.ModuleList([TransformerDecoderLayer(d_model, n_heads, d_ff) for _ in range(n_layers)])
        self.fc_out = nn.Linear(d_model, output_vocab_size)
 
    def forward(self, x, encoder_output, src_mask=None, trg_mask=None):
        x = self.embedding(x)
        x = self.positonal_encoding(x)
        for layer in self.decoder_layers:
            x = layer(x, encoder_output, src_mask, trg_mask)
        output = self.fc_out(x)
        return output
 
class Transformer(nn.Module):
    def __init__(self, d_model, n_heads, n_layers, d_ff, input_vocab_size, output_vocab_size):
        super(Transformer, self).__init__()
        # 编码器
        self.encoder = TransformerEncoder(d_model, n_heads, n_layers, d_ff, input_vocab_size)
        # 解码器
        self.decoder = TransformerDecoder(d_model, n_heads, n_layers, d_ff, output_vocab_size)
 
    def forward(self, src, trg):
        # 源序列mask， 升维，变成(bs, 1, 1, seq_len)
        src_mask = src.unsqueeze(1).unsqueeze(2)
        # 通过编码器得到输出
        encoder_output = self.encoder(src, src_mask)
        # 目标序列mask
        trg_mask = self.create_target_mask(trg)
        # 通过解码器得到输出
        output = self.decoder(trg, encoder_output, src_mask, trg_mask)
        return output
 
    # 创建目标序列的mask， 包括填充部分和未来部分
    def create_target_mask(self, target_data):
        # 形状为(bs, 1, 1, seq_len)
        target_pad_mask = target_data.unsqueeze(1).unsqueeze(2)
        # 获取目标序列的长度，目标序列形状(bs, seq_len)
        trg_len = target_data.size(1)
        # 生成下三角矩阵，对角线及以下元素为True,其余元为False
        trg_subsequent_mask = torch.tril(torch.ones(trg_len, trg_len)).bool()
        # 将填充mask和自回归mask进行结合，逻辑与，得到最终目标序列(bs, 1, seq_len, seq_len)
        trg_mask = target_pad_mask & trg_subsequent_mask
        return trg_mask
 
 
 
# 定义一些参数或者超参数
d_model = 512  # 模型的隐藏层的维度
n_heads = 8  # 注意力头的数量
n_layers = 6  # transformer层的数量
d_ff = 2048  # 前馈神经网络中间层维度
batch_size = 32  # batch
src_seq_length = 20  # 源序列长度
trg_seq_length = 10  # 目标序列长度
input_vocab_size = 10000  # 词汇表的大小
output_vocab_size = 10000  # 词汇表的大小
 
 
transformer = Transformer(d_model, n_heads, n_layers, d_ff, input_vocab_size, output_vocab_size)
src_data = torch.randint(0, input_vocab_size, (batch_size, src_seq_length))
trg_data = torch.randint(0, output_vocab_size, (batch_size, trg_seq_length))
output = transformer(src_data, trg_data)
print(output.shape)