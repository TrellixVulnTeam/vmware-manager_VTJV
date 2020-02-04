'''Main script'''
import os
import threading
import shutil

from tkinter import Tk
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter.simpledialog import askinteger, askstring
from tkinter.messagebox import showerror

import pygubu
from vmrun import Vmrun

from builder import Builder
from logger import TkinterLogger
from namedtuples import Attributes
from pickler import load_state, save_state

VMRUN = 'C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe'


class Application:
    '''The gui class of the application'''

    def __init__(self, root):
        self.root = root
        builder = pygubu.Builder()
        builder.add_from_file('mainframe.ui')
        builder.get_object('main_frame', root)
        builder.connect_callbacks(self)
        root.protocol("WM_DELETE_WINDOW", self.on_closing)
        root.title('VMware Manager')
        self.builder = Builder(builder)
        self.logger = TkinterLogger(builder)
        self.mother_vm = None

        self.set_attributes(load_state('~/vmware-manager-state'))

    def update_gui(self, attributes):
        '''Updates the gui components'''
        self.builder.set_variable('mother_vm', attributes.mother_vm)
        self.builder.set_variable('output_dir', attributes.output_dir)
        self.builder.set_variable('starting_vm', attributes.starting_vm)
        self.builder.set_variable('ending_vm', attributes.ending_vm)
        self.builder.set_variable('guest_username', attributes.guest_username)
        self.builder.set_variable('guest_password', attributes.guest_password)

    def on_closing(self):
        ''' Callback for on closing event '''
        save_state('~/vmware-manager-state', self.get_attributes())
        self.root.destroy()

    def get_attributes(self):
        '''Returns an attribute class from gui value'''
        obj = {field: self.builder.get_variable(field) for field in Attributes._fields}
        return Attributes(**obj)

    # def set_mother_vm(self):

    def set_attributes(self, state=None):
        '''Sets the attributes for batch processing'''
        if not state:
            attributes = []
            attributes.append(askopenfilename(title='Select mother VM', filetypes=['Vmx *.vmx']))
            attributes.append(askdirectory(title='Select output directory for VMs'))
            attributes.append(askinteger('Enter an integer', 'Starting VM'))
            attributes.append(askinteger('Enter an integer', 'Ending VM'))
            attributes.append(askstring('Enter a string', 'Guest Username'))
            attributes.append(askstring('Enter a string', 'Guest Password'))
            attributes = Attributes(*attributes)
            save_state('~/vmware-manager-state', attributes)
        else:
            attributes = state
        self.mother_vm = self.get_vmx(attributes.mother_vm)
        self.update_gui(attributes)

    def get_vmx(self, vmx_path):
        '''Returns an Vmrun objects using a vmx file path'''
        attributes = self.get_attributes()
        return Vmrun(user=attributes.guest_username, password=attributes.guest_password,
                     vmx=vmx_path, debug=True, vmrun=VMRUN)

    def is_running(self, vmx, vm_list=None):
        '''Returns if an vm is running'''
        if not vm_list:
            vm_list = self.mother_vm.list()
        for running_vm in vm_list[1:]:
            if os.path.samefile(running_vm.rstrip(), vmx):
                return True
        return False

    def clean_vms(self):
        '''Cleans all the vms in a folder'''
        def task():
            attributes = self.get_attributes()
            self.builder.disable_all(self.root)
            self.logger.log('Cleaning VMs...')
            if os.path.exists(attributes.output_dir):
                shutil.rmtree(attributes.output_dir, ignore_errors=True)
            self.builder.enable_all(self.root)
        threading.Thread(target=task, daemon=True).start()

    def set_vars(self):
        '''Cleans all the vms in a folder'''
        # "C:\Program Files\VMware\VMware Tools\vmtoolsd.exe" --cmd "info-get guestinfo.server"
        def task():
            attributes = self.get_attributes()
            self.builder.disable_all(self.root)
            self.logger.log('Settings vars...')
            vm_list = self.mother_vm.list()
            for i in range(attributes.starting_vm, attributes.ending_vm+1):
                vmx = os.path.join(attributes.output_dir, f'worker{i}/worker{i}.vmx')
                vmx = os.path.realpath(vmx)
                if not os.path.exists(vmx):
                    showerror(
                        'VM not found', f'worker{i}.vmx not found. '
                        f'Please make sure all VMs are cloned properly before setting the vars/')
                    self.builder.enable_all(self.root)
                    return
                if self.is_running(vmx, vm_list):
                    showerror('VM is running', f'worker{i}.vmx is running. '
                              f'Please consider closing all the VMs before setting the vars.')
                    self.builder.enable_all(self.root)
                    return

            self.builder.enable_all(self.root)
        threading.Thread(target=task, daemon=True).start()

    def clone_vms(self):
        '''Clones all the vms in a folder'''
        def task():
            attributes = self.get_attributes()
            self.builder.disable_all(self.root)
            for i in range(attributes.starting_vm, attributes.ending_vm+1):
                vmx = os.path.join(attributes.output_dir, f'worker{i}/worker{i}.vmx')
                if os.path.exists(vmx):
                    self.logger.log(f'VM {os.path.basename(vmx)} already exists. Skipping...')
                    continue
                self.logger.log(f'Cloning {os.path.basename(vmx)}..., mode=linked')
                output = self.mother_vm.clone(f'"{vmx}"', 'linked', f'-cloneName=worker{i}')
                if output != []:
                    self.logger.log(f'Error while cloning: {" ".join(output)}')
            self.builder.enable_all(self.root)
        threading.Thread(target=task, daemon=True).start()

    def stop_vm(self, vmx, mode='soft'):
        '''Stops a vm'''
        self.logger.log(f'Stopping {os.path.basename(vmx)}, mode={mode} ...')
        vmrun = self.get_vmx(vmx)
        vmrun.stop(mode)

    def stop_vms(self, mode='soft'):
        '''Stops all the vms'''
        def task():
            attributes = self.get_attributes()
            self.builder.disable_all(self.root)
            self.stop_vm(attributes.mother_vm, mode)
            for i in range(attributes.starting_vm, attributes.ending_vm+1):
                vmx = os.path.join(attributes.output_dir, f'worker{i}/worker{i}.vmx')
                vmx = os.path.realpath(vmx)
                if not os.path.exists(vmx):
                    continue
                self.stop_vm(vmx, mode)
            self.builder.enable_all(self.root)
        threading.Thread(target=task, daemon=True).start()

    def stop_vms_soft(self):
        '''Stops all the vms mode=soft'''
        self.stop_vms(mode='soft')

    def stop_vms_hard(self):
        '''Stops all the vms mode=hard'''
        self.stop_vms(mode='hard')


def main():
    '''Main function of the script'''
    root = Tk()
    Application(root)
    root.mainloop()


if __name__ == '__main__':
    main()
