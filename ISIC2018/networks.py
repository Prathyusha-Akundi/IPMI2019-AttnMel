import torch
import torch.nn as nn
import torch.nn.functional as F
from blocks import AttentionBlock
import torchvision.models as models

class AttnVGG(nn.Module):
    def __init__(self, num_classes, attention=True, normalize_attn=False):
        super(AttnVGG, self).__init__()
        self.attention = attention
        net = models.vgg16_bn(pretrained=True)
        self.conv_block1 = nn.Sequential(*list(net.features.children())[0:6])
        self.conv_block2 = nn.Sequential(*list(net.features.children())[7:13])
        self.conv_block3 = nn.Sequential(*list(net.features.children())[14:23])
        self.conv_block4 = nn.Sequential(*list(net.features.children())[24:33])
        self.conv_block5 = nn.Sequential(*list(net.features.children())[34:43])
        self.pool = nn.AvgPool2d(7, stride=1)
        self.classify = nn.Linear(in_features=512+512+256, out_features=num_classes, bias=True)
        if self.attention:
            self.attn1 = AttentionBlock(256, 512, 256, 4, normalize_attn=normalize_attn)
            self.attn2 = AttentionBlock(512, 512, 256, 2, normalize_attn=normalize_attn)
        # initialize
        self.reset_parameters(self.classify)
        if self.attention:
            self.reset_parameters(self.attn1)
            self.reset_parameters(self.attn2)
    def reset_parameters(self, module):
        for m in module.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, a=0, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1.)
                nn.init.constant_(m.bias, 0.)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0., 0.01)
                nn.init.constant_(m.bias, 0.)
    def forward(self, x):
        block1 = self.conv_block1(x)       # /1
        pool1 = F.max_pool2d(block1, 2, 2) # /2
        block2 = self.conv_block2(pool1)   # /2
        pool2 = F.max_pool2d(block2, 2, 2) # /4
        block3 = self.conv_block3(pool2)   # /4
        pool3 = F.max_pool2d(block3, 2, 2) # /8
        block4 = self.conv_block4(pool3)   # /8
        pool4 = F.max_pool2d(block4, 2, 2) # /16
        block5 = self.conv_block5(pool4)   # /16
        pool5 = F.max_pool2d(block5, 2, 2) # /32
        N, __, __, __ = pool5.size()
        if self.attention:
            g = self.pool(pool5).view(N,512)
            a1, g1 = self.attn1(pool3, pool5)
            a2, g2 = self.attn2(pool4, pool5)
            g_hat = torch.cat((g,g1,g2), dim=1) # batch_size x C
            out = self.classify(g_hat)
        else:
            g = self.pool(pool5).view(N,512)
            g1 = F.adaptive_avg_pool2d(pool3, (1,1)).view(N,-1)
            g2 = F.adaptive_avg_pool2d(pool4, (1,1)).view(N,-1)
            g_hat = torch.cat((g,g1,g2), dim=1) # batch_size x C
            out = self.classify(g_hat)
            a1, a2 = None, None
        return [out, a1, a2]


class VGG(nn.Module):
    def __init__(self, num_classes, attention=None, normalize_attn=None):
        super(VGG, self).__init__()
        self.attention = attention
        net = models.vgg16_bn(pretrained=True)
        self.conv_block1 = nn.Sequential(*list(net.features.children())[0:6])
        self.conv_block2 = nn.Sequential(*list(net.features.children())[7:13])
        self.conv_block3 = nn.Sequential(*list(net.features.children())[14:23])
        self.conv_block4 = nn.Sequential(*list(net.features.children())[24:33])
        self.conv_block5 = nn.Sequential(*list(net.features.children())[34:43])
        self.dense = nn.Sequential(*list(net.classifier.children())[:-1])
        self.classify = nn.Linear(in_features=4096, out_features=num_classes, bias=True)
        # initialize
        self.reset_parameters(self.classify)
    def reset_parameters(self, module):
        for m in module.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, a=0, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1.)
                nn.init.constant_(m.bias, 0.)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0., 0.01)
                nn.init.constant_(m.bias, 0.)
    def forward(self, x):
        block1 = self.conv_block1(x)       # /1
        pool1 = F.max_pool2d(block1, 2, 2) # /2
        block2 = self.conv_block2(pool1)   # /2
        pool2 = F.max_pool2d(block2, 2, 2) # /4
        block3 = self.conv_block3(pool2)   # /4
        pool3 = F.max_pool2d(block3, 2, 2) # /8
        block4 = self.conv_block4(pool3)   # /8
        pool4 = F.max_pool2d(block4, 2, 2) # /16
        block5 = self.conv_block5(pool4)   # /16
        pool5 = F.max_pool2d(block5, 2, 2) # /32
        N, __, __, __ = pool5.size()
        g = self.dense(pool5.view(N,-1))
        out = self.classify(g)
        a1, a2 = None, None
        return [out, a1, a2]