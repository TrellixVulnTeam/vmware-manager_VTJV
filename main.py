'''Main script'''
import os
import threading
import shutil

from tkinter import Tk
from tkinter.messagebox import showerror

from vmrun import Vmrun

from vmx import read_vmx, write_vmx
from gui import Gui

VMRUN = 'C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe'


class StopIterationException(Exception):
    '''Raised when the iternation needs to be terminated'''


def iterate_check_exists_cb(mother_vm_path, vmx_path, index):
    '''Iterate callback for checking if all the vms are found'''
    if not os.path.exists(vmx_path):
        showerror('VM not found', f'worker{index}.vmx not found. '
                  f'Please make sure all VMs are cloned properly.')
        raise StopIterationException


class Application(Gui):
    '''The gui class of the application'''

    def __init__(self, root):
        Gui.__init__(self, root)

    def iterate(self, callback, include_mother_vms=False):
        '''Iterates through all the vms'''
        def task(i):
            vmx_path = os.path.join(attributes.output_dir, f'worker{i}/worker{i}.vmx')
            vmx_path = os.path.realpath(vmx_path)
            callback(attributes.mother_vm1, vmx_path, i)
        try:
            self.builder.disable_all(self.root)
            attributes = self.get_attributes()
            if include_mother_vms:
                callback(attributes.mother_vm1, attributes.mother_vm1, None)
                callback(attributes.mother_vm2, attributes.mother_vm2, None)
            for i in range(attributes.starting_vm1, attributes.ending_vm1+1):
                task(i)
            for i in range(attributes.starting_vm2, attributes.ending_vm2+1):
                task(i)
            self.builder.enable_all(self.root)
            return True
        except StopIterationException:
            self.builder.enable_all(self.root)
            return False

    def get_mother_vm(self, index):
        '''Returns an Vmrun object of a mother vm'''
        return self.get_vmrun(self.builder.get_variable(f'mother_vm{index}'))

    def get_vmrun(self, vmx_path):
        '''Returns an Vmrun objects using a vmx file path'''
        attributes = self.get_attributes()
        return Vmrun(user=attributes.guest_username, password=attributes.guest_password,
                     vmx=vmx_path, debug=True, vmrun=VMRUN)

    def is_running(self, vmx_path, vm_list=None):
        '''Returns if an vm is running'''
        if not vm_list:
            vm_list = self.get_mother_vm(1).list()
        for running_vm in vm_list[1:]:
            if os.path.samefile(running_vm.rstrip(), vmx_path):
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

        vm_list = self.get_mother_vm(1).list()

        def check_running_cb(mother_vm_path, vmx_path, index):
            '''Iterate callback for checking if any vm is running'''
            if self.is_running(vmx_path, vm_list):
                showerror('VM is running', f'worker{index}.vmx is running. '
                          f'Please consider closing all the VMs.')
                raise StopIterationException

        def iterate_cb(mother_vm_path, vmx_path, index):
            self.logger.log(f'Writing variables to {os.path.basename(vmx_path)}...')
            vmx = read_vmx(vmx_path)
            vmx['guestinfo.server'] = os.environ['COMPUTERNAME']
            vmx['guestinfo.worker'] = index
            write_vmx(vmx_path, vmx)

        def task():
            if self.iterate(iterate_check_exists_cb) and self.iterate(check_running_cb):
                self.iterate(iterate_cb)
        threading.Thread(target=task, daemon=True).start()

    def start_vms(self):
        '''Starts all the vms'''
        vm_list = self.get_mother_vm(1).list()

        def iterate_cb(mother_vm_path, vmx_path, index):
            if self.is_running(vmx_path, vm_list):
                self.logger.log(f'worker{index}.vmx is already running. Skipping...')
                return
            self.logger.log(f'Starting {os.path.basename(vmx_path)}...')
            vmrun = self.get_vmrun(vmx_path)
            print(vmrun.start())

        def task():
            if self.iterate(iterate_check_exists_cb):
                self.iterate(iterate_cb)
        threading.Thread(target=task, daemon=True).start()

    def clone_vms(self):
        '''Clones all the vms in a folder'''
        def iterate_cb(mother_vm_path, vmx_path, index):
            if os.path.exists(vmx_path):
                self.logger.log(f'VM {os.path.basename(vmx_path)} already exists. Skipping...')
                return
            self.logger.log(f'Cloning {os.path.basename(vmx_path)}..., mode=linked')
            vmrun = self.get_vmrun(mother_vm_path)
            output = vmrun.clone(f'"{vmx_path}"', 'linked', f'-cloneName=worker{index}')
            if output != []:
                self.logger.log(" ".join(output))
        threading.Thread(target=lambda: self.iterate(iterate_cb), daemon=True).start()

    def stop_vm(self, vmx_path, mode='soft'):
        '''Stops a vm'''
        self.logger.log(f'Stopping {os.path.basename(vmx_path)}, mode={mode} ...')
        vmrun = self.get_vmrun(vmx_path)
        vmrun.stop(mode)

    def stop_vms(self, mode='soft'):
        '''Stops all the vms'''
        def iterate_cb(mother_vm_path, vmx_path, index):
            if not os.path.exists(vmx_path):
                return
            self.stop_vm(vmx_path, mode)
        threading.Thread(target=lambda: self.iterate(iterate_cb, True), daemon=True).start()

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
