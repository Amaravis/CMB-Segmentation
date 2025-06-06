import numpy as np
from PIL import Image
import torch
import pdb
import torch.nn.functional as F
from torch.autograd import Variable
from math import exp

def MAE(img1, img2, l1loss):
	return l1loss(img1,img2).item()

def PSNR(img1, img2, mseloss, data_range):
	# you could also use skimage
	# import skimage
	# skimage.metrics.peak_signal_noise_ratio(img1.numpy(), (img2*0.99).numpy(),data_range=data_range)
	return 10*torch.log10( (data_range*data_range) / mseloss(img1,img2) )

def gaussian(window_size, sigma):
	gauss = torch.Tensor([exp(-(x - window_size//2)**2/float(2*sigma**2)) for x in range(window_size)])
	return gauss/gauss.sum()

def create_window(window_size, channel):
	_1D_window = gaussian(window_size, 1.5).unsqueeze(1)
	_2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
	window = Variable(_2D_window.expand(channel, 1, window_size, window_size).contiguous())
	return window

def create_window_3D(window_size, channel):
	_1D_window = gaussian(window_size, 1.5).unsqueeze(1)
	_2D_window = _1D_window.mm(_1D_window.t())
	_3D_window = _1D_window.mm(_2D_window.reshape(1, -1)).reshape(window_size, window_size, window_size).float().unsqueeze(0).unsqueeze(0)
	window = Variable(_3D_window.expand(channel, 1, window_size, window_size, window_size).contiguous())
	return window

def _ssim(img1, img2, window, window_size, channel, size_average = True):
	mu1 = F.conv2d(img1, window, padding = window_size//2, groups = channel)
	mu2 = F.conv2d(img2, window, padding = window_size//2, groups = channel)

	mu1_sq = mu1.pow(2)
	mu2_sq = mu2.pow(2)
	mu1_mu2 = mu1*mu2

	sigma1_sq = F.conv2d(img1*img1, window, padding = window_size//2, groups = channel) - mu1_sq
	sigma2_sq = F.conv2d(img2*img2, window, padding = window_size//2, groups = channel) - mu2_sq
	sigma12 = F.conv2d(img1*img2, window, padding = window_size//2, groups = channel) - mu1_mu2

	C1 = 0.01**2
	C2 = 0.03**2

	ssim_map = ((2*mu1_mu2 + C1)*(2*sigma12 + C2))/((mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2))

	if size_average:
		return ssim_map.mean()
	else:
		return ssim_map.mean(1).mean(1).mean(1)
	
def _ssim_3D(img1, img2, window, window_size, channel, size_average = True):
	mu1 = F.conv3d(img1, window, padding = window_size//2, groups = channel)
	mu2 = F.conv3d(img2, window, padding = window_size//2, groups = channel)

	mu1_sq = mu1.pow(2)
	mu2_sq = mu2.pow(2)

	mu1_mu2 = mu1*mu2

	sigma1_sq = F.conv3d(img1*img1, window, padding = window_size//2, groups = channel) - mu1_sq
	sigma2_sq = F.conv3d(img2*img2, window, padding = window_size//2, groups = channel) - mu2_sq
	sigma12 = F.conv3d(img1*img2, window, padding = window_size//2, groups = channel) - mu1_mu2

	C1 = 0.01**2
	C2 = 0.03**2

	ssim_map = ((2*mu1_mu2 + C1)*(2*sigma12 + C2))/((mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2))

	if size_average:
		return ssim_map.mean()
	else:
		return ssim_map.mean(1).mean(1).mean(1)
	


class SSIM(torch.nn.Module):
	def __init__(self, window_size = 11, size_average = True):
		super(SSIM, self).__init__()
		self.window_size = window_size
		self.size_average = size_average
		self.channel = 1
		self.window = create_window(window_size, self.channel)

	def forward(self, img1, img2):
		(_, channel, _, _) = img1.size()

		if channel == self.channel and self.window.data.type() == img1.data.type():
			window = self.window
		else:
			window = create_window(self.window_size, channel)
			
			if img1.is_cuda:
				window = window.cuda(img1.get_device())
			window = window.type_as(img1)
			
			self.window = window
			self.channel = channel


		return _ssim(img1, img2, window, self.window_size, channel, self.size_average)
	
	
class SSIM3D(torch.nn.Module):
	def __init__(self, window_size = 11, size_average = True):
		super(SSIM3D, self).__init__()
		self.window_size = window_size
		self.size_average = size_average
		self.channel = 1
		self.window = create_window_3D(window_size, self.channel)

	def ssim_3D(self, img1, img2, window, window_size, channel, size_average = True):
		mu1 = F.conv3d(img1, window, padding = window_size//2, groups = channel)
		mu2 = F.conv3d(img2, window, padding = window_size//2, groups = channel)

		mu1_sq = mu1.pow(2)
		mu2_sq = mu2.pow(2)

		mu1_mu2 = mu1*mu2

		sigma1_sq = F.conv3d(img1*img1, window, padding = window_size//2, groups = channel) - mu1_sq
		sigma2_sq = F.conv3d(img2*img2, window, padding = window_size//2, groups = channel) - mu2_sq
		sigma12 = F.conv3d(img1*img2, window, padding = window_size//2, groups = channel) - mu1_mu2

		C1 = 0.01**2
		C2 = 0.03**2

		ssim_map = ((2*mu1_mu2 + C1)*(2*sigma12 + C2))/((mu1_sq + mu2_sq + C1)*(sigma1_sq + sigma2_sq + C2))

		if size_average:
			return ssim_map.mean()
		else:
			return ssim_map.mean(1).mean(1).mean(1)
	
	def forward(self, img1, img2):
		(_, channel, _, _, _) = img1.size()

		if channel == self.channel and self.window.data.type() == img1.data.type():
			window = self.window
		else:
			window = create_window_3D(self.window_size, channel)
			
			if img1.is_cuda:
				window = window.cuda(img1.get_device())
			window = window.type_as(img1)
			
			self.window = window
			self.channel = channel


		return self.ssim_3D(img1, img2, window, self.window_size, channel, self.size_average)

	
def ssim(img1, img2, window_size = 11, size_average = True):
	(_, channel, _, _) = img1.size()
	window = create_window(window_size, channel)
	
	if img1.is_cuda:
		window = window.cuda(img1.get_device())
	window = window.type_as(img1)
	
	return _ssim(img1, img2, window, window_size, channel, size_average)

def ssim3D(img1, img2, window_size = 11, size_average = True):
	(_, channel, _, _, _) = img1.size()
	window = create_window_3D(window_size, channel)
	
	if img1.is_cuda:
		window = window.cuda(img1.get_device())
	window = window.type_as(img1)
	
	return _ssim_3D(img1, img2, window, window_size, channel, size_average)

if __name__ == "__main__":
	# pdb.set_trace()
	origin_img = torch.rand((256,256,256))
	generate_img = torch.clone(origin_img)
	print(origin_img.shape)

	# MAE is L1Loss, 0 is the ideal
	L1Loss=torch.nn.L1Loss()
	print('MAE score: ', MAE(origin_img, generate_img, L1Loss))

	# Peak Signal to Noise Ratio (PSNR), bigger is better
	MSE_loss = torch.nn.MSELoss()
	# normally, 8 bit color image's range should be 255
	data_range = 10 
	print('PSNR score: ', PSNR(origin_img, generate_img*0.99, MSE_loss, data_range))

	# Structural Similarity Metric (SSIM), 1 is the ideal
	# https://github.com/jinh0park/pytorch-ssim-3D
	# input should be shape (batch_size, channel, long, width, height)
	img1 = origin_img.cuda()
	img1 = torch.unsqueeze(img1,0)
	img1 = torch.unsqueeze(img1,0)
	img2 = generate_img.cuda()
	img2 = torch.unsqueeze(img2,0)
	img2 = torch.unsqueeze(img2,0)

	# SSIM function
	print(ssim3D(img1,img2).item())
	# SSIM class (loss)
	ssim_loss = SSIM3D(window_size=11)
	print(ssim_loss(img1,img2))


	pdb.set_trace()